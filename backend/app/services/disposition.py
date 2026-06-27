"""Recovery Disposition — the four-outcome decision, made explicit and inspectable.

A recovery is never simply "done / not done." This read-only classifier maps an incident's CURRENT ground
truth onto the disposition vocabulary the domain already defines —

    VERIFIED · CONDITIONAL · FAILED · INSUFFICIENT_EVIDENCE · ESCALATION_REQUIRED  (else IN_PROGRESS)

— and exposes two things that keep the system honest:

1. **Hard closure invariants** — closure requires EVERY one of (machine/production conditions PASSED,
   quality conditions PASSED, verification window complete, required evidence present & fresh, required
   approvals complete). A low False-Closure-Risk score can never substitute for a missing invariant: the
   score is advisory; these are mandatory. ``can_close`` is exactly the deterministic evaluator's verdict.
2. **Human-status matrix** — technician (work) vs telemetry (machine) vs quality (release). When these
   disagree (e.g. work COMPLETED but telemetry FAILED or quality on HOLD), the system refuses to pick a
   winner and recommends **escalation** rather than forcing certainty.

This NEVER decides closure or changes state — the deterministic evaluator owns the verdict (see
``services/evaluator.py``); this only *composes* that verdict with the evidence/approval/intervention facts
the system already records. Advisory & read-only. Synthetic PROTOTYPE_ASSUMPTION data.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.domain.enums import ConditionKind, InterventionStatus, Role, WorkflowState
from app.domain.models import (
    ApprovalDecision,
    Incident,
    Intervention,
    RecoveryCondition,
    RecoveryContract,
)
from app.services.comparable_conditions import assess_comparability
from app.services.evaluator import evaluate
from app.services.quality import quality_release_satisfied
from app.services.recovery_policy import (
    ELIGIBLE,
    FAILED,
    INSUFFICIENT,
    RULE_VERSION,
    confounders_of,
    derive_effective_recovery_confidence,
)

# plain-language meaning for each disposition (keep the technical key, add a human label)
DISPOSITION_META = {
    "VERIFIED": "Verified — every recovery requirement passed.",
    "CONDITIONAL": "Conditional — production may continue under temporary restrictions while recovery completes.",
    "FAILED": "Failed — a recovery requirement was violated.",
    "INSUFFICIENT_EVIDENCE": "Insufficient evidence — telemetry alone is not enough to responsibly decide.",
    "ESCALATION_REQUIRED": "Escalation required — human signals disagree; no automatic winner.",
    "IN_PROGRESS": "In progress — still gathering stable cycles and evidence.",
}


def _technician_status(session: Session, incident_id: str) -> str:
    ivs = session.exec(
        select(Intervention).where(Intervention.incident_id == incident_id)
        .order_by(Intervention.sequence.desc())  # type: ignore[attr-defined]
    ).all()
    active = next((iv for iv in ivs if iv.status != InterventionStatus.SUPERSEDED), ivs[0] if ivs else None)
    return active.status.value.lower() if active else "none"  # completed | in_progress | proposed | none


def _quality_status(session: Session, contract_id: str, conditions: list[dict]) -> str:
    q_ok, _ = quality_release_satisfied(session, contract_id)
    if q_ok:
        return "released"
    denied = session.exec(
        select(ApprovalDecision).where(ApprovalDecision.contract_id == contract_id)
        .where(ApprovalDecision.decision == "deny")
    ).all()
    if any(d.decided_role == Role.QUALITY_ENGINEER for d in denied):
        return "hold"
    if any(c["kind"] == ConditionKind.QUALITY.value and c["status"] == "VIOLATED" for c in conditions):
        return "hold"
    return "pending"


def _telemetry_status(ev) -> str:
    """Machine/production side only — independent of the quality gate (so 'telemetry stable, quality
    missing' is expressible)."""
    machine = [c for c in ev.conditions if c["kind"] != ConditionKind.QUALITY.value]
    if any(c["status"] == "VIOLATED" for c in machine):
        return "failed"
    window_complete = ev.stable_streak >= ev.required_stable_cycles
    if window_complete and machine and all(c["status"] == "PASSED" for c in machine):
        return "stable"
    return "monitoring"


def assess_disposition(session: Session, incident: Incident) -> dict:
    contract = (session.get(RecoveryContract, incident.current_contract_id)
                if incident.current_contract_id else None)
    if contract is None:
        return {"available": False, "incident_id": incident.id,
                "reason": "No recovery contract yet — disposition is available once one is drafted."}

    ev = evaluate(session, contract)

    machine_conds = [c for c in ev.conditions if c["kind"] != ConditionKind.QUALITY.value]
    quality_conds = [c for c in ev.conditions if c["kind"] == ConditionKind.QUALITY.value]
    q_ok, q_reason = quality_release_satisfied(session, contract.id)

    def _passed(conds: list[dict]) -> int:
        return sum(1 for c in conds if c["status"] == "PASSED")

    invariants = [
        {"key": "machine", "label": "Machine & production conditions passed",
         "ok": bool(machine_conds) and all(c["status"] == "PASSED" for c in machine_conds),
         "detail": f"{_passed(machine_conds)}/{len(machine_conds)} passed"},
        {"key": "quality", "label": "Quality conditions passed",
         "ok": bool(quality_conds) and all(c["status"] == "PASSED" for c in quality_conds),
         "detail": f"{_passed(quality_conds)}/{len(quality_conds)} passed"},
        {"key": "window", "label": "Verification window complete",
         "ok": ev.stable_streak >= ev.required_stable_cycles,
         "detail": f"{ev.stable_streak}/{ev.required_stable_cycles} stable cycles"},
        {"key": "evidence", "label": "Required evidence present & fresh",
         "ok": not ev.blocked_keys,
         "detail": ("missing/stale: " + ", ".join(ev.blocked_keys)) if ev.blocked_keys else "all present & fresh"},
        {"key": "approvals", "label": "Required approvals complete",
         "ok": q_ok, "detail": q_reason},
    ]
    technician = _technician_status(session, incident.id)
    telemetry = _telemetry_status(ev)
    quality = _quality_status(session, contract.id, ev.conditions)
    window_complete = ev.stable_streak >= ev.required_stable_cycles
    machine_ok = window_complete and bool(machine_conds) and all(c["status"] == "PASSED" for c in machine_conds)
    comp = assess_comparability(session, incident)
    comparable = comp.get("classification", "UNKNOWN")
    confounders = confounders_of(comp)
    # raw causal confidence (for provenance); the disposition decision rests on hard-gate + comparability.
    from app.services.recovery_signature import score_signature
    raw_conf = (score_signature(session, contract).alignment + 1.0) / 2.0
    # disagreement: work reported done, but the machine or quality says otherwise (not a formal violation)
    conflict = (technician == "completed" and (telemetry == "failed" or quality == "hold")
                and ev.verdict != "verified")

    # the deterministic hard-gate state the evaluator already decided → fed to the canonical ceiling policy
    if ev.verdict == "violated":
        evidence_status = FAILED
    elif ev.verdict == "verified":
        evidence_status = ELIGIBLE
    elif machine_ok:
        evidence_status = INSUFFICIENT   # telemetry recovered, but a hard gate (quality/evidence) is unmet
    else:
        evidence_status = None           # still gathering cycles — not yet a decision point
    policy = (derive_effective_recovery_confidence(
        raw_conf, comparable, comp.get("confidence_multiplier") or 0.5, evidence_status, confounders=confounders)
        if evidence_status is not None else None)

    # classify (terminal/disagreement first; then the single canonical ceiling policy)
    reasons: list[str] = []
    if incident.state == WorkflowState.ESCALATED:
        disposition = "ESCALATION_REQUIRED"
        reasons.append(f"Incident escalated after {incident.reopened_count} failed recovery attempt(s).")
    elif ev.verdict == "violated":
        disposition = "FAILED"
        reasons.append(f"Contract violated: {', '.join(ev.violated_keys)}.")
    elif quality == "hold" and telemetry == "stable":
        disposition = "ESCALATION_REQUIRED"
        reasons.append("Telemetry is stable but quality placed a HOLD — conflicting signals; escalate.")
    elif conflict:
        disposition = "ESCALATION_REQUIRED"
        reasons.append("Work reported complete but the machine/quality disagrees — escalate, don't force closure.")
    elif policy is not None:
        disposition = policy.policy_result          # VERIFIED | INSUFFICIENT_EVIDENCE | FAILED (canonical)
        reasons.extend(policy.notes)
        if disposition == "INSUFFICIENT_EVIDENCE":
            unmet = [i["label"] for i in invariants if not i["ok"]]
            if unmet:
                reasons.append("Unmet hard invariant(s): " + "; ".join(unmet) + ".")
    else:
        disposition = "IN_PROGRESS"
        reasons.append(f"Monitoring: {ev.stable_streak}/{ev.required_stable_cycles} stable cycles.")

    # always surface comparability when it is not clean (even if another reason drives the disposition)
    if comparable != "COMPARABLE":
        reasons.append(f"Comparable conditions: {comparable.replace('_', ' ').lower()}"
                       + (f" (shifted: {', '.join(confounders)})" if confounders else "") + ".")

    # can_close = the canonical policy result, NOT the raw evaluator verdict: a NOT_COMPARABLE/UNKNOWN
    # recovery can never represent a closeable verified recovery (rule ccr-1.0).
    can_close = bool(policy and policy.policy_result == "VERIFIED")
    provenance = (policy.as_provenance() if policy
                  else {"comparability_classification": comparable, "policy_result": "IN_PROGRESS",
                        "rule_version": RULE_VERSION})

    return {
        "available": True,
        "incident_id": incident.id,
        "disposition": disposition,
        "meaning": DISPOSITION_META[disposition],
        "decided": disposition != "IN_PROGRESS",
        "can_close": can_close,
        "verdict": ev.verdict,
        "effective_confidence": (policy.effective_confidence if policy else None),
        "reasons": reasons,
        "hard_invariants": invariants,
        "human_status": {
            "technician": technician,   # completed | in_progress | proposed | none
            "telemetry": telemetry,     # stable | monitoring | failed
            "quality": quality,         # released | pending | hold
            "supervisor": "not_captured",  # honest gap: supervisor production intent isn't modeled yet
        },
        "conflict": conflict or (quality == "hold" and telemetry == "stable"),
        "comparability": {"classification": comparable,
                          "confidence_multiplier": comp.get("confidence_multiplier"),
                          "key_shifts": comp.get("key_shifts", 0),
                          "confounding_dimensions": confounders},
        "policy_provenance": provenance,
        "stable_cycles": ev.stable_streak,
        "required_stable_cycles": ev.required_stable_cycles,
        "basis": ("Advisory & read-only. The deterministic evaluator owns the hard closure gate; this composes "
                  "that verdict with the Comparable-Conditions ceiling (rule ccr-1.0). can_close requires EVERY "
                  "hard invariant AND comparable conditions — a low risk score or good comparability can never "
                  "substitute for a missing hard gate, and a missing/unknown comparability can never be called "
                  "verified. Synthetic prototype."),
    }
