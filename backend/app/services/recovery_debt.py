"""Recovery Debt — the conditional-recovery (concession / deviation permit) lifecycle.

A Recovery Debt lets production continue under explicit, time-boxed restrictions while a *waivable*
recovery condition is not yet met — so a CONDITIONAL recovery can never silently become a permanent
closure. It is GRANTED only by an authorised human through the Agent Action Gateway (APPROVAL_REQUIRED;
see tools/registry.py), and it must end one of two ways: **SETTLED** (the waived condition later verifies)
or **BREACHED** at expiry → auto-escalation.

Hard guard: a debt can never waive a relapse (fault non-recurrence), a quality condition, or anything
safety-bearing — those are precisely what the product exists to protect (mirrors the gateway's PROHIBITED
set philosophy). Read paths are read-only; settle/breach mutate + transition and are audited. Grant lives
in the gateway handler so it passes identity → role → policy → human-approval → audit like every write.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.domain.base import utcnow
from app.domain.enums import (
    AuditEventType,
    CompareOp,
    ConditionKind,
    OutcomeType,
    RecoveryDebtStatus,
    Role,
    WorkflowState,
)
from app.domain.models import Incident, RecoveryCondition, RecoveryContract, RecoveryDebt
from app.services.evaluator import evaluate
from app.workflow.audit import record_audit
from app.workflow.state_machine import transition

_TERMINAL = (WorkflowState.VERIFIED_RECOVERY, WorkflowState.ESCALATED, WorkflowState.CANCELLED)


def unwaivable_reason(cond: RecoveryCondition) -> Optional[str]:
    """Why a condition may NOT be waived (None ⇒ waivable). The product's safety core, applied to debt."""
    if cond.kind == ConditionKind.QUALITY:
        return "quality conditions cannot be waived (they require a quality release, not a concession)"
    if cond.op == CompareOp.NOT_RECUR:
        return "fault non-recurrence cannot be waived (a relapse is a hard failure, never a concession)"
    blob = f"{cond.key} {cond.label or ''}".lower()
    if "safety" in blob or "interlock" in blob:
        return "safety-bearing conditions cannot be waived"
    return None


def validate_waivable(session: Session, contract: RecoveryContract, keys: list[str]) -> list[dict]:
    """Return ``[{key, reason}]`` for every requested key that may NOT be waived (unknown or protected)."""
    conds = {c.key: c for c in session.exec(
        select(RecoveryCondition).where(RecoveryCondition.contract_id == contract.id)).all()}
    problems: list[dict] = []
    for k in keys:
        c = conds.get(k)
        if c is None:
            problems.append({"key": k, "reason": "no such condition on the contract"})
            continue
        reason = unwaivable_reason(c)
        if reason:
            problems.append({"key": k, "reason": reason})
    return problems


def active_debt(session: Session, incident: Incident) -> Optional[RecoveryDebt]:
    return session.exec(
        select(RecoveryDebt).where(RecoveryDebt.incident_id == incident.id)
        .where(RecoveryDebt.status == RecoveryDebtStatus.ACTIVE)
        .order_by(RecoveryDebt.granted_at.desc())  # type: ignore[attr-defined]
    ).first()


def latest_debt(session: Session, incident: Incident) -> Optional[RecoveryDebt]:
    return session.exec(
        select(RecoveryDebt).where(RecoveryDebt.incident_id == incident.id)
        .order_by(RecoveryDebt.granted_at.desc())  # type: ignore[attr-defined]
    ).first()


def is_breached(debt: RecoveryDebt, as_of: Optional[datetime] = None) -> bool:
    return debt.status == RecoveryDebtStatus.ACTIVE and (as_of or utcnow()) > debt.expires_at


def settle_recovery_debt(session: Session, incident: Incident, *, actor: str = "system",
                         role: Role = Role.SYSTEM) -> Optional[RecoveryDebt]:
    """Settle the active debt IFF every waived condition now PASSES (deterministic — the debt is paid back).
    Returns the debt (SETTLED if it qualified, still ACTIVE if not), or None if there is no active debt."""
    debt = active_debt(session, incident)
    if debt is None:
        return None
    if is_breached(debt):
        return debt  # an expired debt must be swept/escalated, not settled
    contract = session.get(RecoveryContract, debt.contract_id)
    ev = evaluate(session, contract)
    status_by_key = {c["key"]: c["status"] for c in ev.conditions}
    unmet = [k for k in debt.waived_condition_keys if status_by_key.get(k) != "PASSED"]
    if unmet:
        return debt  # still owed — the waived condition has not verified yet
    debt.status = RecoveryDebtStatus.SETTLED
    debt.settled_at = utcnow()
    debt.settled_by = actor
    debt.resolution_note = "Waived condition(s) later verified — debt settled."
    session.add(debt)
    record_audit(session, type=AuditEventType.RECOVERY_DEBT_SETTLED, correlation_id=incident.correlation_id,
                 actor=actor, role=role,
                 summary=f"Recovery debt settled — {', '.join(debt.waived_condition_keys)} verified.",
                 incident_id=incident.id, contract_id=debt.contract_id,
                 detail={"debt_id": debt.id, "waived": debt.waived_condition_keys})
    session.flush()
    return debt


def sweep_recovery_debt(session: Session, incident: Incident, *,
                        as_of: Optional[datetime] = None) -> Optional[RecoveryDebt]:
    """If the active debt has expired unsettled → BREACH it and auto-escalate. Never a silent closure."""
    debt = active_debt(session, incident)
    if debt is None or not is_breached(debt, as_of):
        return debt
    debt.status = RecoveryDebtStatus.BREACHED
    debt.resolution_note = "Waiver expired before the condition was verified — auto-escalated."
    session.add(debt)
    record_audit(session, type=AuditEventType.RECOVERY_DEBT_BREACHED, correlation_id=incident.correlation_id,
                 actor="system", role=Role.SYSTEM,
                 summary=f"Recovery debt BREACHED (expired {debt.expires_at.isoformat()}) — escalating.",
                 incident_id=incident.id, contract_id=debt.contract_id, detail={"debt_id": debt.id})
    if incident.state not in _TERMINAL:
        transition(session, incident, WorkflowState.ESCALATED, actor="system", role=Role.SYSTEM,
                   reason="recovery-debt breach: the conditional waiver expired unsettled")
        incident.outcome_type = OutcomeType.ESCALATED
        incident.outcome_summary = ("Escalated — a recovery-debt waiver expired before the waived "
                                    "condition was verified.")
        session.add(incident)
    session.flush()
    return debt


def debt_view(session: Session, incident: Incident, *, as_of: Optional[datetime] = None) -> dict:
    as_of = as_of or utcnow()
    debt = latest_debt(session, incident)
    if debt is None:
        return {"available": False, "incident_id": incident.id,
                "reason": "No recovery debt on this incident."}
    breached_now = is_breached(debt, as_of)
    remaining_s = (max(0.0, (debt.expires_at - as_of).total_seconds())
                   if debt.status == RecoveryDebtStatus.ACTIVE else 0.0)
    conds = {c.key: c for c in session.exec(
        select(RecoveryCondition).where(RecoveryCondition.contract_id == debt.contract_id)).all()}
    waived = [{"key": k, "label": (conds[k].label if k in conds else k)} for k in debt.waived_condition_keys]
    return {
        "available": True,
        "incident_id": incident.id,
        "debt_id": debt.id,
        "status": ("BREACHED" if breached_now else debt.status.value),
        "active": debt.status == RecoveryDebtStatus.ACTIVE and not breached_now,
        "waived": waived,
        "reason": debt.reason,
        "restrictions": debt.restrictions,
        "monitoring_requirement": debt.monitoring_requirement,
        "follow_up": debt.follow_up,
        "granted_by": debt.granted_by,
        "granted_role": (debt.granted_role.value if debt.granted_role else None),
        "granted_at": debt.granted_at.isoformat(),
        "expires_at": debt.expires_at.isoformat(),
        "minutes_remaining": round(remaining_s / 60.0, 1),
        "settled_at": debt.settled_at.isoformat() if debt.settled_at else None,
        "settled_by": debt.settled_by or None,
        "resolution_note": debt.resolution_note or None,
        "basis": ("A conditional-recovery waiver (a concession / deviation permit). Granted by an authorised "
                  "human via the Agent Action Gateway; it never waives a relapse, quality, or safety; it must "
                  "SETTLE (the waived condition verifies) or it BREACHES at expiry and auto-escalates — it can "
                  "never silently become a permanent closure. Synthetic PROTOTYPE_ASSUMPTION."),
    }
