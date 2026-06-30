"""Recovery Mission Spine — one mission object, seven stages.

The cure for "a collection of dashboards": this projects an incident onto a single seven-stage spine —
Intake → Reconstruction → Recovery Contract → Evidence Plan → Verification → Release Decision →
Qualification Record — and answers, at a glance, the four questions a plant always has:

    where does the mission stand · what is blocking it · who must act next · why isn't it VERIFIED yet.

It is a read-only projection of facts the system already records (lifecycle state + interventions +
contract + the deterministic evaluator + disposition). It decides nothing and changes no state.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.domain.enums import WorkflowState
from app.domain.models import Incident, Intervention, RecoveryContract
from app.services.disposition import assess_disposition
from app.services.evaluator import evaluate

STAGES = ["Intake", "Reconstruction", "Recovery Contract", "Evidence Plan",
          "Verification", "Release Decision", "Qualification Record"]


def assess_mission(session: Session, incident: Incident) -> dict:
    # Reconstruction is "done" once an intervention is diagnosed OR the incident was reconstructed from an
    # uploaded export (the intake analysis is stored on the incident).
    has_intervention = (
        session.exec(select(Intervention).where(Intervention.incident_id == incident.id)).first() is not None
        or bool(getattr(incident, "intake", None))
    )
    contract = (session.get(RecoveryContract, incident.current_contract_id)
                if incident.current_contract_id else None)
    has_contract = contract is not None
    ev = evaluate(session, contract) if contract else None
    disp = assess_disposition(session, incident) if contract else None

    evidence_ok = bool(ev) and not ev.blocked_keys
    window_complete = bool(ev) and ev.stable_streak >= ev.required_stable_cycles
    disposition = disp["disposition"] if (disp and disp.get("available")) else "IN_PROGRESS"
    can_close = bool(disp and disp.get("can_close"))
    decided = disposition in ("VERIFIED", "FAILED", "ESCALATION_REQUIRED")
    approvals_ok = bool(disp and next((i for i in disp["hard_invariants"] if i["key"] == "approvals"), {}).get("ok"))
    contract_reviewed = has_contract and incident.state != WorkflowState.RECOVERY_CONTRACT_DRAFTED

    done = [
        True,                                              # Intake
        has_intervention,                                  # Reconstruction
        contract_reviewed,                                 # Recovery Contract (drafted + reviewed)
        bool(has_contract and evidence_ok),                # Evidence Plan
        window_complete,                                   # Verification
        decided,                                           # Release Decision (a terminal decision reached)
        bool(disposition == "VERIFIED" and can_close),     # Qualification Record
    ]
    current = next((i for i, d in enumerate(done) if not d), len(STAGES))  # len = complete
    complete = current == len(STAGES)

    # is the current stage *blocked* (vs simply in-progress)?
    blocked = (current == 3) or (current == 5 and not can_close) or disposition in ("FAILED", "ESCALATION_REQUIRED")
    cyc = f"{ev.stable_streak}/{ev.required_stable_cycles} stable cycles" if ev else ""

    summaries = [
        "Incident captured" + (f" · {incident.fault_code}" if incident.fault_code else ""),
        "Intervention diagnosed & recorded" if has_intervention else "Awaiting agent triage / diagnosis",
        ("Recovery Contract reviewed" if contract_reviewed else "Contract drafted — awaiting review") if has_contract else "No contract yet",
        ("Required evidence present & fresh" if evidence_ok else "Collecting required evidence") if has_contract else "Pending contract",
        (cyc if not window_complete else f"Window complete · {cyc}") if ev else "Pending monitoring",
        (disposition.replace("_", " ").title() if disp and disp.get("available") else "Pending decision"),
        "Qualification Record issued" if (disposition == "VERIFIED" and can_close) else "Pending verified release",
    ]

    def status(i: int) -> str:
        if done[i]:
            return "done"
        if i == current:
            return "blocked" if blocked else "active"
        return "pending"

    stages = [{"index": i, "name": STAGES[i], "status": status(i), "summary": summaries[i]} for i in range(len(STAGES))]

    # who must act next
    if disposition == "VERIFIED":
        who = "Complete — Qualification Record is issued."
    elif not has_contract:
        who = "Supervisor — draft & review the Recovery Contract."
    elif not contract_reviewed:
        who = "Supervisor — review the Recovery Contract."
    elif not approvals_ok:
        who = "Quality Engineer — record the quality release."
    elif disposition == "ESCALATION_REQUIRED":
        who = "Plant supervision — resolve the escalation."
    elif not window_complete:
        who = "No human action yet — monitoring the verification window."
    else:
        who = "Supervisor — review the release decision."

    what_blocks = ("Nothing — all release gates passed." if disposition == "VERIFIED"
                   else (disp["reasons"][0] if (disp and disp.get("reasons")) else "Gathering stable cycles & evidence."))

    return {
        "available": True,
        "incident_id": incident.id,
        "current_index": current,
        "current_stage": STAGES[min(current, len(STAGES) - 1)],
        "complete": complete,
        "outcome": disposition,
        "can_close": can_close,
        "reopened_count": incident.reopened_count,
        "what_blocks": what_blocks,
        "who_next": who,
        "why_not_verified": (disp["reasons"] if (disp and disposition != "VERIFIED") else []),
        "stages": stages,
        "basis": ("A read-only projection of the incident lifecycle + the deterministic evaluator + "
                  "disposition. It sequences the existing surfaces into one mission; it changes no state "
                  "and decides nothing."),
    }
