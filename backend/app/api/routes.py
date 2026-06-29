"""Read views + gateway-mediated actions. All mutations go through the gateway or the orchestrator
(which itself routes side effects through the gateway)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlmodel import Session, select

from app.api import serializers as S
from app.auth import Principal, get_principal
from app.composition import build_port, build_reasoning, build_recovery_service
from app.config import get_settings
from app.db import get_session
from app.domain.models import ApprovalRequirement, EvidenceRequirement, Incident, RecoveryContract
from app.gateway import execute as gateway_execute
from app.workflow.recovery_service import RecoveryService

router = APIRouter(prefix="/api", tags=["recovery"])
_settings = get_settings()


def _incident(session: Session, incident_id: str) -> Incident:
    inc = session.get(Incident, incident_id)
    if inc is None:
        raise HTTPException(404, f"incident {incident_id} not found")
    return inc


def _svc(session: Session) -> RecoveryService:
    # Constructed via the composition root so "which adapter / which model" lives in one place.
    return build_recovery_service(session)


# ── identity ─────────────────────────────────────────────────────────────────
@router.get("/me")
def me(principal: Principal = Depends(get_principal)) -> dict:
    from app.security import permissions_for

    return {"user_id": principal.user_id, "username": principal.username, "role": principal.role.value,
            "plant_id": principal.plant_id, "tenant_id": principal.tenant_id,
            "permissions": permissions_for(principal.role),
            "environment": _settings.environment, "demo_mode": _settings.demo_mode}


@router.get("/metrics")
def metrics(session: Session = Depends(get_session)) -> dict:
    """Operational SLIs (uptime, request/error counters, latency percentiles, status mix) + mission KPIs."""
    from app.observability import snapshot

    incidents = session.exec(select(Incident).where(Incident.historical == False)).all()  # noqa: E712
    terminal = {"VERIFIED_RECOVERY", "CANCELLED", "ESCALATED"}
    snap = snapshot()
    snap["missions"] = {
        "active": len([i for i in incidents if i.state.value not in terminal]),
        "verified": len([i for i in incidents if i.state.value == "VERIFIED_RECOVERY"]),
        "reopened_total": sum(i.reopened_count for i in incidents),
    }
    return snap


# ── reads ────────────────────────────────────────────────────────────────────
@router.get("/missions")
def missions(session: Session = Depends(get_session)) -> dict:
    incidents = session.exec(select(Incident).where(Incident.historical == False)).all()  # noqa: E712
    rows = [S.mission_summary(session, i) for i in incidents]
    session.commit()
    rows.sort(key=lambda r: (not r["is_active"], r["state"]))
    return {"missions": rows, "environment": _settings.environment}


@router.get("/missions/{incident_id}")
def mission(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    out = S.mission_detail(session, inc)
    session.commit()
    return out


@router.get("/incidents/{incident_id}/contract")
def incident_contract(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    if inc.current_contract_id is None:
        raise HTTPException(404, "no contract yet")
    contract = session.get(RecoveryContract, inc.current_contract_id)
    out = S.contract_view(session, contract)
    session.commit()
    return out


@router.get("/contracts/{contract_id}")
def contract(contract_id: str, session: Session = Depends(get_session)) -> dict:
    c = session.get(RecoveryContract, contract_id)
    if c is None:
        raise HTTPException(404, "contract not found")
    out = S.contract_view(session, c)
    session.commit()
    return out


@router.get("/incidents/{incident_id}/contract-versions")
def contract_versions(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    contracts = session.exec(
        select(RecoveryContract).where(RecoveryContract.incident_id == inc.id).order_by(RecoveryContract.version)  # type: ignore[arg-type]
    ).all()
    out = [S.contract_view(session, c) for c in contracts]
    session.commit()
    return {"versions": out}


@router.get("/incidents/{incident_id}/evidence")
def evidence(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    out = S.evidence_view(session, inc)
    session.commit()
    return out


@router.get("/incidents/{incident_id}/timeline")
def timeline(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    return S.timeline_view(session, inc)


@router.get("/incidents/{incident_id}/outcome")
def outcome(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    out = S.outcome_view(session, inc)
    session.commit()
    return out


@router.get("/incidents/{incident_id}/audit")
def audit(incident_id: str, session: Session = Depends(get_session)) -> dict:
    from app.workflow.audit import verify_audit_chain

    inc = _incident(session, incident_id)
    return {"events": S.audit_view(session, inc),
            "integrity": verify_audit_chain(session, inc.correlation_id)}


@router.get("/incidents/{incident_id}/audit/verify")
def audit_verify(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Recompute the audit hash chain and report tamper-evidence (compliance/integrity check)."""
    from app.workflow.audit import verify_audit_chain

    inc = _incident(session, incident_id)
    return verify_audit_chain(session, inc.correlation_id)


@router.get("/notifications")
def notifications(session: Session = Depends(get_session),
                  principal: Principal = Depends(get_principal)) -> dict:
    from app.services import notifications as notify

    rows = notify.list_for(session, role=principal.role)
    return {"notifications": [S.notification_view(n) for n in rows],
            "unread": notify.unread_count(session, role=principal.role),
            "role": principal.role.value}


@router.post("/notifications/{notification_id}/read")
def notification_read(notification_id: str, session: Session = Depends(get_session),
                      principal: Principal = Depends(get_principal)) -> dict:
    from app.services import notifications as notify

    note = notify.mark_read(session, notification_id)
    if note is None:
        raise HTTPException(404, "notification not found")
    session.commit()
    return {"ok": True, "status": note.status}


@router.get("/incidents/{incident_id}/reasoning")
def reasoning(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    return S.reasoning_view(session, inc)


@router.get("/incidents/{incident_id}/forecast")
def forecast(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Recovery Forecaster — predicts whether the repair will hold, before the fault recurs (advisory)."""
    inc = _incident(session, incident_id)
    return S.forecast_view(session, inc)


@router.get("/incidents/{incident_id}/signature")
def signature(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Expected Recovery Signature — advisory intervention-consistency: did the line recover the way THIS
    intervention should have caused it to (vs. temporary suppression / changed conditions / noise)? The
    expected signature is derived from the contract's own conditions. Read-only; never changes the verdict."""
    inc = _incident(session, incident_id)
    return S.signature_view(session, inc)


@router.get("/incidents/{incident_id}/decision")
def decision(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Decision Intelligence — risk-adjusted cost/impact, recommended option, and an FMEA (advisory)."""
    from app.services.decision import decide

    inc = _incident(session, incident_id)
    return decide(session, inc)


@router.get("/incidents/{incident_id}/reliability")
def reliability(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Reliability statistics — how confident, mathematically, the recovery verdict is: the zero-failure
    reliability-demonstration test (confidence vs. stable cycles, cycles needed for a target), a window
    grade, and a bathtub-curve hazard read. Advisory — never changes the deterministic verdict."""
    from app.services.reliability_stats import assess

    inc = _incident(session, incident_id)
    return assess(session, inc)


@router.get("/incidents/{incident_id}/provenance")
def provenance(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Closure provenance — why the outcome was decided and whether it can be trusted: the deterministic
    conditions, trust-weighted evidence, human approvals, interventions, a proposed-vs-executed
    reconciliation, and audit-chain integrity. Read-only; assembled independently of the LLM."""
    from app.services.provenance import closure_provenance

    inc = _incident(session, incident_id)
    return closure_provenance(session, inc)


@router.get("/incidents/{incident_id}/certificate")
def certificate(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Return-to-Service (Recovery) Certificate — the exportable proof of recovery: verdict, conditions,
    trust-weighted evidence, human signatures, intervention-consistency, and the tamper-evident audit seal.
    Read-only; composed from the deterministic verdict + provenance (never the LLM)."""
    from app.services.certificate import build_certificate

    inc = _incident(session, incident_id)
    return build_certificate(session, inc)


@router.get("/incidents/{incident_id}/closure-risk")
def closure_risk(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """False-Closure Risk Score — an explainable, advisory estimate of how likely closing *now* would be a
    false closure, with each contributing factor. Read-only; never gates closure (the evaluator owns it)."""
    from app.services.false_closure_risk import assess_false_closure_risk

    inc = _incident(session, incident_id)
    return assess_false_closure_risk(session, inc)


@router.get("/incidents/{incident_id}/oee-restoration")
def oee_restoration(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """OEE-Restoration Verification — did the recovery restore OEE (Availability × Performance × Quality)
    to baseline, or just close the order? Recomputes A·P·Q over the verification window vs the machine
    baseline and flags which factor still lags. Read-only & advisory; the evaluator owns closure."""
    from app.services.oee_restoration import assess_oee_restoration

    inc = _incident(session, incident_id)
    return assess_oee_restoration(session, inc)


@router.get("/incidents/{incident_id}/disposition")
def disposition(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Recovery Disposition — the four-outcome decision made explicit: VERIFIED / CONDITIONAL / FAILED /
    INSUFFICIENT_EVIDENCE / ESCALATION_REQUIRED (else IN_PROGRESS), the hard closure invariants (each
    pass/fail), and the technician↔telemetry↔quality status matrix. Read-only; the evaluator owns closure."""
    from app.services.disposition import assess_disposition

    inc = _incident(session, incident_id)
    out = assess_disposition(session, inc)
    session.commit()  # evaluate() refreshes condition rows — persist them like the other evaluating GETs
    return out


@router.get("/incidents/{incident_id}/comparability")
def comparability(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Comparable-Conditions Gate — did before/after run under conditions we can responsibly compare?
    Returns COMPARABLE / PARTIALLY_COMPARABLE / NOT_COMPARABLE / UNKNOWN with a per-dimension breakdown.
    Read-only & advisory; guards against attributing a confound to the intervention."""
    from app.services.comparable_conditions import assess_comparability

    inc = _incident(session, incident_id)
    return assess_comparability(session, inc)


@router.get("/incidents/{incident_id}/recovery-debt")
def recovery_debt(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """The conditional-recovery waiver (concession) on this incident, if any — status, waived condition(s),
    restrictions, expiry, monitoring, follow-up. Read-only."""
    from app.services.recovery_debt import debt_view

    inc = _incident(session, incident_id)
    return debt_view(session, inc)


class GrantDebtBody(BaseModel):
    waived_condition_keys: list[str]
    reason: str
    restrictions: list[str] = []
    expires_in_minutes: int = 90
    monitoring_requirement: str = ""
    follow_up: str = ""


@router.post("/incidents/{incident_id}/recovery-debt/grant")
def grant_recovery_debt(incident_id: str, body: GrantDebtBody, session: Session = Depends(get_session),
                        principal: Principal = Depends(get_principal)) -> dict:
    """Grant a time-boxed conditional-recovery waiver — routed through the Agent Action Gateway as an
    APPROVAL_REQUIRED action (an authorised human only; never waives a relapse/quality/safety)."""
    inc = _incident(session, incident_id)
    out = gateway_execute(session, tool_name="grant_recovery_debt",
                          raw_args={"incident_id": incident_id, **body.model_dump()}, principal=principal,
                          correlation_id=inc.correlation_id, incident_id=incident_id,
                          port=build_port(session), reasoning=build_reasoning())
    session.commit()
    return out.model_dump(mode="json")


@router.post("/incidents/{incident_id}/recovery-debt/settle")
def settle_recovery_debt_route(incident_id: str, session: Session = Depends(get_session),
                               principal: Principal = Depends(get_principal)) -> dict:
    """Settle the active waiver IFF the waived condition has now verified (deterministic). Read-back the debt."""
    from app.services.recovery_debt import debt_view, settle_recovery_debt

    inc = _incident(session, incident_id)
    settle_recovery_debt(session, inc, actor=principal.username, role=principal.role)
    session.commit()
    return debt_view(session, inc)


@router.post("/incidents/{incident_id}/recovery-debt/sweep")
def sweep_recovery_debt_route(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Breach-check the active waiver: if expired unsettled → BREACH + auto-escalate. Read-back the debt."""
    from app.services.recovery_debt import debt_view, sweep_recovery_debt

    inc = _incident(session, incident_id)
    sweep_recovery_debt(session, inc)
    session.commit()
    return debt_view(session, inc)


@router.get("/incidents/{incident_id}/sensor-trust")
def sensor_trust(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Sensor Trust Gate — TRUSTED / DEGRADED / UNTRUSTED / UNKNOWN per machine sensor, from deterministic
    checks (range/flatline/noise/calibration). An untrusted or unknown sensor can't satisfy a hard condition."""
    from app.services.sensor_trust import assess_sensor_trust

    inc = _incident(session, incident_id)
    return assess_sensor_trust(session, inc)


@router.get("/incidents/{incident_id}/lot-at-risk")
def lot_at_risk(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Lot-at-Risk — last-good / first-questionable cycle, affected window + lots + disposition, and the
    required quality action (a recommendation only; never auto-releases or quarantines product)."""
    from app.services.lot_at_risk import assess_lot_at_risk

    inc = _incident(session, incident_id)
    return assess_lot_at_risk(session, inc)


@router.get("/incidents/{incident_id}/maia-messages")
def maia_messages(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """The structured MAIA/WhatsApp outbound message(s) applicable to this incident right now. Communication
    surface only — deep-links into the app, never tool execution. Read-only."""
    from app.integration.efficast.maia import MAIA_KINDS, maia_messages_for

    inc = _incident(session, incident_id)
    return {"messages": [m.model_dump(mode="json") for m in maia_messages_for(session, inc)], "kinds": MAIA_KINDS}


@router.get("/stakeholder-views")
def stakeholder_views() -> dict:
    """All role-specific view contracts (what each persona sees / may do / may approve)."""
    from app.services.stakeholder_view import all_stakeholder_views

    return {"views": all_stakeholder_views()}


@router.get("/stakeholder-view")
def my_stakeholder_view(principal: Principal = Depends(get_principal)) -> dict:
    """The current principal's role-specific view."""
    from app.services.stakeholder_view import view_for_role

    return view_for_role(principal.role.value)


@router.get("/incidents/{incident_id}/sensitivity")
def sensitivity(incident_id: str, session: Session = Depends(get_session)) -> dict:
    """Counterfactual contract calibration — replays the deterministic verifier over the real trajectory
    at a sweep of verification-window lengths to find the minimum-safe window and which thresholds would
    have falsely closed before the relapse. Advisory — never changes the verdict."""
    from app.services.sensitivity import analyze

    inc = _incident(session, incident_id)
    return analyze(session, inc)


@router.get("/calibration")
def calibration(trials: int = 400) -> dict:
    """Calibration harness for the Expected Recovery Signature — Brier / reliability curve / ROC-AUC over
    seeded synthetic scenarios. Read-only, advisory, reproducible. Makes the advisory layer falsifiable
    (synthetic PROTOTYPE_ASSUMPTION — measures the signature's internal skill, not real plant recovery)."""
    from app.services.calibration import run_calibration

    return run_calibration(trials=min(max(trials, 100), 2000))


# ── front of the loop: MAIA alerts + agent diagnosis ──────────────────────────
@router.get("/alerts")
def alerts(session: Session = Depends(get_session)) -> dict:
    return {"alerts": S.open_alerts_view(session), "environment": _settings.environment}


@router.get("/machine-profiles")
def machine_profiles() -> dict:
    """The machine-agnostic contract catalog (supported equipment classes)."""
    return S.machine_profiles_view()


@router.get("/troubleshoot")
def troubleshoot(fault_code: Optional[str] = None, machine_model: Optional[str] = None,
                 q: str = "", session: Session = Depends(get_session)) -> dict:
    """Grounded troubleshooting lookup: approved procedure + ranked causes + history + signals +
    captured lessons for a fault/machine — so a plant person finds the answer without hunting."""
    from app.services.troubleshooting import troubleshoot as _ts

    return _ts(session, fault_code=fault_code, machine_model=machine_model, query=q)


@router.get("/knowledge")
def knowledge(session: Session = Depends(get_session)) -> dict:
    """Institutional knowledge base — candidate + curated lessons from past recoveries."""
    from app.services.knowledge import list_candidates

    rows = [S.knowledge_view(k) for k in list_candidates(session)]
    return {"knowledge": rows,
            "pending": len([r for r in rows if r["status"] == "PENDING_REVIEW"]),
            "approved": len([r for r in rows if r["status"] == "APPROVED"])}


class ReviewBody(BaseModel):
    decision: str = "approve"  # approve | reject
    reason: str = ""

    @field_validator("decision")
    @classmethod
    def _decision_explicit(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("decision must be exactly 'approve' or 'reject'")
        return v


@router.post("/knowledge/{candidate_id}/review")
def review_knowledge(candidate_id: str, body: ReviewBody, session: Session = Depends(get_session),
                     principal: Principal = Depends(get_principal)) -> dict:
    """Curate a candidate lesson into institutional knowledge (reviewer-role-gated)."""
    from app.services.knowledge import review_knowledge as _review

    kc = _review(session, candidate_id, principal, decision=body.decision, reason=body.reason)
    session.commit()
    return {"ok": True, "status": kc.status.value, "reviewed_by": kc.reviewed_by}


@router.get("/governance")
def governance(session: Session = Depends(get_session)) -> dict:
    """Live governance & compliance posture: security, logging, auditability, reliability,
    control-framework alignment, and honest gaps."""
    from app.services.governance import posture

    return posture(session)


@router.get("/security")
def security(session: Session = Depends(get_session)) -> dict:
    """Live security posture: edge hardening (headers, rate limiting, body guard), keyed audit
    signing + integrity, the classified security-event detection stream, and honest gaps."""
    from app.services.security_posture import posture

    return posture(session)


@router.get("/integration")
def integration(session: Session = Depends(get_session)) -> dict:
    """ISA-95 hierarchy, Unified-Namespace topics, and the connector catalog."""
    return S.integration_view(session)


@router.get("/integration/shadow")
def shadow_scorecard() -> dict:
    """Tier-0 Shadow Mode Scorecard — runs the deterministic cores over labeled contract-v0.1 event bundles,
    compares each verdict to the outcome the plant published, and reports agreement, a confusion matrix,
    Cohen's κ, and false-closure detection — writing NOTHING (writes_performed=0). The artifact an Efficast
    evaluator would ask for before trusting (or connecting) anything."""
    from app.services.shadow_scorecard import run_scorecard

    return run_scorecard()


@router.get("/incidents/{incident_id}/diagnosis")
def diagnosis(incident_id: str, session: Session = Depends(get_session)) -> dict:
    inc = _incident(session, incident_id)
    return S.diagnosis_view(session, inc)


@router.post("/alerts/{alert_id}/triage")
def triage_alert(alert_id: str, session: Session = Depends(get_session),
                 principal: Principal = Depends(get_principal)) -> dict:
    from app.adapters.efficast_port import MaiaAlertDTO
    from app.domain.models import MaiaAlert

    row = session.get(MaiaAlert, alert_id)
    if row is None:
        raise HTTPException(404, f"alert {alert_id} not found")
    dto = MaiaAlertDTO(
        id=row.id, source=row.source, kind=row.kind, machine_id=row.machine_id, order_id=row.order_id,
        fault_code=row.fault_code,
        severity=row.severity.value if hasattr(row.severity, "value") else str(row.severity),
        message=row.message, signals=row.signals or {}, detected_at=row.detected_at, status=row.status,
    )
    inc = _svc(session).triage_from_alert(dto)
    session.commit()
    return {"ok": True, "incident_id": inc.id, "state": inc.state.value,
            "diagnosis": S.diagnosis_view(session, inc)}


@router.post("/incidents/{incident_id}/diagnosis/accept")
def accept_diagnosis(incident_id: str, session: Session = Depends(get_session),
                     principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    _svc(session).accept_diagnosis(inc, principal)
    session.commit()
    return {"ok": True, "state": inc.state.value}


# ── generic gateway tool call (every action passes the gateway) ───────────────
class ToolCall(BaseModel):
    args: dict = {}
    incident_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@router.post("/tools/{tool_name}")
def call_tool(tool_name: str, body: ToolCall, session: Session = Depends(get_session),
              principal: Principal = Depends(get_principal)) -> dict:
    inc = session.get(Incident, body.incident_id) if body.incident_id else None
    correlation = inc.correlation_id if inc else "adhoc"
    out = gateway_execute(session, tool_name=tool_name, raw_args=body.args, principal=principal,
                          correlation_id=correlation, incident_id=body.incident_id,
                          idempotency_key=body.idempotency_key, port=build_port(session),
                          reasoning=build_reasoning())
    session.commit()
    return out.model_dump(mode="json")


# ── orchestrated human/agent actions ─────────────────────────────────────────
class AdvanceBody(BaseModel):
    n: int = 1


class EvidenceBody(BaseModel):
    value_num: Optional[float] = None
    value_text: str = ""
    unit: str = ""
    source: str = ""


class ApprovalBody(BaseModel):
    decision: str = "approve"  # approve | reject
    reason: str = ""

    @field_validator("decision")
    @classmethod
    def _decision_explicit(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("decision must be exactly 'approve' or 'reject'")
        return v


class TelemetryReading(BaseModel):
    vibration: Optional[float] = None
    temperature: Optional[float] = None
    cycle_time: Optional[float] = None
    scrap_pct: Optional[float] = None
    fault_code: Optional[str] = None
    extra: dict = {}


class TelemetryBody(BaseModel):
    readings: list[TelemetryReading]


@router.post("/telemetry/{machine_id}")
def ingest_telemetry(machine_id: str, body: TelemetryBody, session: Session = Depends(get_session),
                     principal: Principal = Depends(get_principal)) -> dict:
    """Ingest real telemetry readings for a machine. They are consumed FIFO by the next verification
    window instead of synthetic samples — the same evaluator then verifies recovery on real data.
    This is the seam a real Efficast Edge / historian stream would feed (see docs/REAL_DATA_INTEGRATION.md)."""
    from app.domain.base import utcnow
    from app.domain.models import Machine, TelemetrySample
    from sqlalchemy import func as _func

    machine = session.get(Machine, machine_id)
    if machine is None:
        raise HTTPException(404, f"machine {machine_id} not found")
    start = int(session.exec(
        select(_func.max(TelemetrySample.seq)).where(TelemetrySample.machine_id == machine_id)
    ).one() or 0)
    for i, r in enumerate(body.readings, start=1):
        session.add(TelemetrySample(
            tenant_id=machine.tenant_id, machine_id=machine_id, seq=start + i,
            vibration=r.vibration, temperature=r.temperature, cycle_time=r.cycle_time,
            scrap_pct=r.scrap_pct, fault_code=r.fault_code, extra=r.extra, source="ingested",
            received_at=utcnow(),
        ))
    session.commit()
    return {"ok": True, "machine_id": machine_id, "ingested": len(body.readings),
            "next_seq": start + len(body.readings)}


@router.post("/incidents/{incident_id}/contract/draft")
def draft(incident_id: str, session: Session = Depends(get_session),
          principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    c = _svc(session).draft_contract(inc)
    session.commit()
    return {"ok": True, "contract_id": c.id, "state": inc.state.value}


@router.post("/incidents/{incident_id}/contract/review")
def review(incident_id: str, session: Session = Depends(get_session),
           principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    _svc(session).review_contract(inc, principal)
    session.commit()
    return {"ok": True, "state": inc.state.value}


@router.post("/evidence/{requirement_id}/submit")
def submit_evidence(requirement_id: str, body: EvidenceBody, session: Session = Depends(get_session),
                    principal: Principal = Depends(get_principal)) -> dict:
    req = session.get(EvidenceRequirement, requirement_id)
    if req is None:
        raise HTTPException(404, "evidence requirement not found")
    inc = _incident(session, req.incident_id)
    out = _svc(session).submit_evidence(inc, principal, requirement_id=requirement_id,
                                        value_num=body.value_num, value_text=body.value_text,
                                        unit=body.unit, source=body.source)
    session.commit()
    return out.model_dump(mode="json")


@router.post("/approvals/{requirement_id}/decide")
def decide(requirement_id: str, body: ApprovalBody, session: Session = Depends(get_session),
           principal: Principal = Depends(get_principal)) -> dict:
    req = session.get(ApprovalRequirement, requirement_id)
    if req is None:
        raise HTTPException(404, "approval requirement not found")
    inc = _incident(session, req.incident_id)
    out = _svc(session).record_approval(inc, principal, requirement_id=requirement_id,
                                        decision=body.decision, reason=body.reason)
    session.commit()
    return out.model_dump(mode="json")


@router.post("/incidents/{incident_id}/monitoring/start")
def start_monitoring(incident_id: str, session: Session = Depends(get_session),
                     principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    _svc(session).start_monitoring(inc)
    session.commit()
    return {"ok": True, "state": inc.state.value}


@router.post("/incidents/{incident_id}/advance")
def advance(incident_id: str, body: AdvanceBody, session: Session = Depends(get_session),
            principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    out = _svc(session).advance(inc, body.n)
    session.commit()
    return out


@router.post("/incidents/{incident_id}/contingency/approve")
def approve_contingency(incident_id: str, session: Session = Depends(get_session),
                        principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    _svc(session).approve_contingency(inc, principal)
    session.commit()
    return {"ok": True, "state": inc.state.value}


@router.post("/incidents/{incident_id}/contingency/complete")
def complete_contingency(incident_id: str, session: Session = Depends(get_session),
                         principal: Principal = Depends(get_principal)) -> dict:
    inc = _incident(session, incident_id)
    _svc(session).complete_contingency(inc)
    session.commit()
    return {"ok": True, "state": inc.state.value}
