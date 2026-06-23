"""Closure provenance — "why did the system decide this, and can we trust the closure?"

A dashboard shows numbers; a *traceable operational system* can reconstruct a decision. This assembles
the queryable provenance of an incident's outcome from the data the system already records — the
deterministic conditions, the **trust-weighted** evidence, the human approvals, the interventions, and a
**reconciliation** of what the agent *proposed* against what actually *executed* (logs alone are not
proof) — plus the tamper-evident audit-chain integrity. It answers a regulator's / a buyer's question:
*who requested the recovery, which evidence supported it, who approved it, what changed, and why it
closed or reopened.*

This lives **beside** the deterministic evaluator, not inside the LLM layer: the agent proposes a
reasoning path, but provenance independently records what happened. Read-only; it never changes state.
Retrieved document content is treated as untrusted input throughout (see the gateway/RAG layers).

References: AI decision provenance / data lineage (actors, versions, timestamps, rationale → an auditable
chain of custody). See docs/PROVENANCE.md.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.domain.enums import WorkflowState
from app.domain.models import (
    ActionProposal,
    ApprovalDecision,
    EvidenceItem,
    EvidenceRequirement,
    Incident,
    Intervention,
    RecoveryCondition,
    RecoveryContract,
    ToolExecution,
)
from app.services.evidence_quality import classify, summarize
from app.workflow.audit import verify_audit_chain


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def _reconcile(session: Session, incident: Incident) -> dict:
    """Independently reconcile proposed actions against actual executions — self-reported ≠ proof.

    Flags any proposal that claims ``executed`` without a tool-execution record, any proposal left stuck
    ``proposed``, and any execution with no owning proposal (an action that bypassed the proposal step)."""
    proposals = session.exec(
        select(ActionProposal).where(ActionProposal.incident_id == incident.id)
    ).all()
    execs = session.exec(
        select(ToolExecution).where(ToolExecution.incident_id == incident.id)
    ).all()
    exec_proposal_ids = {e.proposal_id for e in execs if e.proposal_id}
    proposal_ids = {p.id for p in proposals}

    unreconciled: list[dict] = []
    for p in proposals:
        if p.status == "executed" and p.id not in exec_proposal_ids:
            unreconciled.append({"proposal_id": p.id, "tool": p.tool_name,
                                 "issue": "marked executed but has no tool-execution record"})
        elif p.status == "proposed":
            unreconciled.append({"proposal_id": p.id, "tool": p.tool_name,
                                 "issue": "proposed but never resolved (no execute/deny/fail)"})
    orphans = [e.id for e in execs if e.proposal_id and e.proposal_id not in proposal_ids]

    return {
        "proposed": len(proposals),
        "executed": sum(1 for p in proposals if p.status == "executed"),
        "failed": sum(1 for p in proposals if p.status == "failed"),
        "denied": sum(1 for p in proposals if p.status == "denied"),
        "unreconciled": unreconciled,
        "orphan_executions": orphans,
        "ok": not unreconciled and not orphans,
    }


def closure_provenance(session: Session, incident: Incident) -> dict:
    """The full provenance record for an incident's recovery decision (advisory, read-only)."""
    contract = (session.get(RecoveryContract, incident.current_contract_id)
                if incident.current_contract_id else None)
    if contract is None:
        return {"available": False, "incident_id": incident.id,
                "reason": "No recovery contract yet — provenance is available once one is drafted."}

    # 1. deterministic conditions (the basis of the verdict)
    conditions = [
        {"key": c.key, "kind": c.kind.value, "op": c.op.value, "status": c.status.value, "label": c.label}
        for c in session.exec(select(RecoveryCondition).where(RecoveryCondition.contract_id == contract.id)).all()
    ]
    violated = [c["key"] for c in conditions if c["status"] == "VIOLATED"]

    # 2. trust-weighted evidence
    reqs = {r.id: r for r in session.exec(
        select(EvidenceRequirement).where(EvidenceRequirement.incident_id == incident.id)).all()}
    items = session.exec(
        select(EvidenceItem).where(EvidenceItem.incident_id == incident.id)
        .order_by(EvidenceItem.received_at)  # type: ignore[arg-type]
    ).all()
    evidence = [classify(i, reqs.get(i.requirement_id)) for i in items]
    evidence_summary = summarize(evidence)

    # 3. human approvals (who authorised what)
    approvals = [
        {"decided_by": a.decided_by, "decided_role": a.decided_role.value, "decision": a.decision,
         "reason": a.reason, "at": _iso(a.decided_at)}
        for a in session.exec(
            select(ApprovalDecision).where(ApprovalDecision.incident_id == incident.id)
            .order_by(ApprovalDecision.decided_at)  # type: ignore[arg-type]
        ).all()
    ]

    # 4. interventions (what was done — including a failed first attempt)
    interventions = [
        {"sequence": iv.sequence, "kind": iv.kind, "title": iv.title, "status": iv.status.value}
        for iv in session.exec(
            select(Intervention).where(Intervention.incident_id == incident.id)
            .order_by(Intervention.sequence)  # type: ignore[arg-type]
        ).all()
    ]

    # 5. reconciliation (self-reported vs actual) + 6. audit-chain integrity
    reconciliation = _reconcile(session, incident)
    audit = verify_audit_chain(session, incident.correlation_id)

    closed = incident.state == WorkflowState.VERIFIED_RECOVERY
    trustworthy = (audit.get("ok") and reconciliation["ok"]
                   and (evidence_summary["min_trust"] or 0) > 0)

    if closed:
        summary = (
            f"Recovery VERIFIED. {len(conditions)} contract conditions evaluated by the deterministic "
            f"verifier, {evidence_summary['count']} evidence items (mean trust "
            f"{evidence_summary['mean_trust']}), {len(approvals)} human approval(s). "
            f"Proposed↔executed {'reconciled' if reconciliation['ok'] else 'NOT reconciled'}; "
            f"audit chain {'intact' if audit.get('ok') else 'BROKEN'} ({audit.get('count')} entries)."
        )
    elif incident.reopened_count:
        summary = (
            f"Incident reopened ×{incident.reopened_count}"
            + (f" — condition(s) {', '.join(violated)} VIOLATED" if violated else "")
            + f". Not closed (state {incident.state.value}). Provenance preserved across the reopen."
        )
    else:
        summary = (f"In progress (state {incident.state.value}). "
                   f"{evidence_summary['count']} evidence items so far; closure not yet decided.")

    return {
        "available": True,
        "incident_id": incident.id,
        "state": incident.state.value,
        "outcome_type": incident.outcome_type.value if incident.outcome_type else None,
        "closed": closed,
        "reopened_count": incident.reopened_count,
        "violated_conditions": violated,
        "conditions": conditions,
        "evidence": evidence,
        "evidence_summary": evidence_summary,
        "approvals": approvals,
        "interventions": interventions,
        "reconciliation": reconciliation,
        "audit": audit,
        "trustworthy": bool(trustworthy),
        "summary": summary,
        "note": ("Independent of the LLM: the agent proposes a reasoning path, but this record is "
                 "assembled from the deterministic verifier, the gateway's proposal/execution log, and "
                 "the tamper-evident audit chain. Advisory & read-only."),
    }
