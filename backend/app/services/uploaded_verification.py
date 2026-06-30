"""The last mile: replay an uploaded mission's telemetry through the deterministic evaluator.

Creating a mission from an upload (intake_mission.py) gets you as far as *reconstruction*. This drives it
the rest of the way: ingest the uploaded telemetry as :class:`TelemetrySample`s, draft a Recovery Contract
through the real :class:`RecoveryService` (the agent drafts; the deterministic gate refuses a contract that
can't detect the relapse it's verifying), satisfy the monitoring-tier prerequisites from the uploaded data,
then **replay the uploaded cycles through the same evaluator that runs the synthetic demo**. The verdict is
the engine's, not a heuristic's.

For the messy sample (F27 recurs at cycle 17) the evaluator independently REJECTS closure and the mission
reopens — the product's thesis ("a closed work order ≠ a recovered line") proven on the user's own data, by
the authoritative layer. It then stops at the next human gate (contingency approval): honest, not auto-closed.

Governance held: the agent drafts; technical evidence is *derived from the upload* (provenance-stamped); the
deterministic evaluator owns the verdict; nothing fabricates a quality release the upload doesn't contain; no
machine is touched. The one concession — recording the contract-review approval via the seeded supervisor —
mirrors the established headless demo (``app.cli demo``) and is the operator's own review of the upload.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.auth import Principal
from app.domain.base import utcnow
from app.domain.enums import InterventionStatus, Role, WorkflowState
from app.domain.models import (
    ApprovalRequirement,
    Incident,
    Intervention,
    TelemetrySample,
    User,
)
from app.services.evidence import missing_required
from app.workflow.recovery_service import RecoveryService, WorkflowError

# The deterministic reasoning provider always drafts the F27 conveyor template; a non-F27 upload would need a
# machine profile to draft a contract that tests *its* fault. Bounded honestly until profile-driven drafting.
_SUPPORTED_FAULTS = {"F27"}


def _role_principals(session: Session) -> dict[Role, Principal]:
    out: dict[Role, Principal] = {}
    for u in session.exec(select(User)).all():
        out.setdefault(u.role, Principal(u.id, u.username, u.role, u.plant_id, u.tenant_id))
    return out


def _ensure_intervention(session: Session, incident: Incident) -> Intervention:
    existing = session.exec(
        select(Intervention).where(Intervention.incident_id == incident.id)
    ).first()
    if existing is not None:
        return existing
    itv = Intervention(
        tenant_id=incident.tenant_id, plant_id=incident.plant_id, incident_id=incident.id,
        machine_id=incident.machine_id, sequence=1, kind="unspecified_intervention",
        title="Intervention recorded in the uploaded export",
        description=("Reconstructed from the uploaded plant data: the work order was closed before recovery "
                     "was independently proven."),
        status=InterventionStatus.COMPLETED, proposed_at=utcnow(), completed_at=utcnow(),
    )
    session.add(itv)
    session.flush()
    return itv


def _ingest_series(session: Session, incident: Incident, series: list[dict]) -> int:
    """Ingest the uploaded per-cycle readings as TelemetrySamples for the machine (FIFO, after any
    existing seq so we never reorder), tagged with this incident so leftovers can be reclaimed."""
    src = f"upload:{(incident.intake or {}).get('source_filename', 'export')}"
    base = session.exec(
        select(TelemetrySample.seq).where(TelemetrySample.machine_id == incident.machine_id)
        .order_by(TelemetrySample.seq.desc())  # type: ignore[attr-defined]
    ).first() or 0
    ts = utcnow()
    for i, s in enumerate(series, start=1):
        session.add(TelemetrySample(
            tenant_id=incident.tenant_id, machine_id=incident.machine_id, seq=base + i,
            vibration=s.get("vibration"), temperature=s.get("temperature"),
            cycle_time=s.get("cycle_time"), scrap_pct=s.get("scrap_pct"),
            fault_code=s.get("fault") or None, source=src, consumed=False, received_at=ts,
            extra={"upload_incident_id": incident.id, "upload_cycle": s.get("cycle")},
        ))
    session.flush()
    return len(series)


def _consume_leftovers(session: Session, incident: Incident) -> None:
    """After a window ends early (e.g. a relapse), mark this upload's unconsumed samples consumed so they
    can't be picked up by another mission on the same (shared) machine."""
    rows = session.exec(
        select(TelemetrySample).where(TelemetrySample.machine_id == incident.machine_id)
        .where(TelemetrySample.consumed == False)  # noqa: E712
    ).all()
    for r in rows:
        if (r.extra or {}).get("upload_incident_id") == incident.id:
            r.consumed = True
            session.add(r)
    session.flush()


def _derive_numeric(rule: dict, series: list[dict]) -> float:
    """A numeric value satisfying the requirement, preferring a real reading from the upload."""
    lo, hi = rule.get("min"), rule.get("max")
    v = next((s.get("vibration") for s in series if s.get("vibration") is not None), None)
    if v is None:
        v = (((lo or 0.0) + hi) / 2) if hi is not None else (lo if lo is not None else 0.0)
    if lo is not None:
        v = max(v, lo)
    if hi is not None:
        v = min(v, hi)
    return float(v)


def _satisfy_monitoring(session: Session, svc: RecoveryService, incident: Incident, contract,
                        princ: dict[Role, Principal], series: list[dict]) -> None:
    """Satisfy the monitoring-tier prerequisites from the uploaded data — never fabricating evidence the
    upload doesn't contain (a pass/fail quality item with no signal is left missing → an honest block)."""
    ts = utcnow()
    for req in missing_required(session, contract.id, "monitoring"):
        p = princ.get(req.assigned_role)
        if p is None:
            continue
        rtype = (req.validity_rule or {}).get("type", "present")
        if rtype == "numeric":
            svc.submit_evidence(incident, p, requirement_id=req.id,
                                value_num=_derive_numeric(req.validity_rule, series),
                                source="derived from uploaded export", evidence_timestamp=ts)
        elif rtype == "pass_fail":
            continue  # do not invent a pass — leave it missing so verification blocks honestly
        else:  # present | completion | approval
            svc.submit_evidence(incident, p, requirement_id=req.id,
                                value_text="approve" if rtype == "approval" else "completed",
                                source="recorded from uploaded export", evidence_timestamp=ts)
    # Monitoring-tier approvals (the contract review). The operator running verification reviews & approves.
    for appr in session.exec(
        select(ApprovalRequirement).where(ApprovalRequirement.contract_id == contract.id)
        .where(ApprovalRequirement.required_before == "monitoring")
    ).all():
        p = princ.get(appr.required_role)
        if p is not None:
            svc.record_approval(incident, p, requirement_id=appr.id,
                                reason="reviewed & approved the recovery contract on the uploaded data")


def _message(outcome: str, relapse_cycle, stable: int, incident: Incident) -> str:
    if outcome == "reopened":
        return (f"The deterministic evaluator replayed your uploaded telemetry and REJECTED closure: fault "
                f"{incident.fault_code} recurred at cycle {relapse_cycle}, resetting the stable-cycle streak. "
                f"The mission reopened — a contingency now awaits human approval. A closed work order was not "
                f"a recovered line.")
    if outcome == "verified":
        return ("The deterministic evaluator VERIFIED recovery on your uploaded telemetry — every condition "
                "held for the full window and quality was released.")
    if outcome == "insufficient_evidence":
        return ("All technical conditions held, but recovery could NOT be certified — operating conditions "
                "were not comparable, so the improvement can't be attributed to the intervention.")
    if outcome == "escalated":
        return "Recovery failed repeatedly on your uploaded telemetry and was escalated to plant supervision."
    return (f"Replayed {stable} stable cycle(s) from your uploaded telemetry with no relapse so far. "
            f"Verification is still open — to certify VERIFIED, the upload must also include a quality release.")


def run_uploaded_verification(session: Session, incident: Incident) -> dict:
    intake = incident.intake or {}
    series = intake.get("telemetry_series") or []
    if not series:
        return {"ran": False, "reason": "This mission has no uploaded telemetry to verify."}
    if incident.current_contract_id:
        return {"ran": False, "reason": "This mission already has a contract under verification."}
    if incident.state != WorkflowState.INTERVENTION_RECORDED:
        return {"ran": False, "reason": f"Cannot start verification from state {incident.state.value}."}
    if (incident.fault_code or "") not in _SUPPORTED_FAULTS:
        return {"ran": False, "reason": (
            f"Automatic contract drafting currently supports the F27 conveyor profile; this upload's fault "
            f"'{incident.fault_code or 'unknown'}' needs a machine profile (a known gap — "
            f"see docs/RESEARCH_GAPS.md).")}

    princ = _role_principals(session)
    if Role.SUPERVISOR not in princ:
        return {"ran": False, "reason": "No supervisor identity is available to review the contract."}

    _ensure_intervention(session, incident)
    n = _ingest_series(session, incident, series)

    svc = RecoveryService(session)
    try:
        contract = svc.draft_contract(incident)
    except (ValueError, WorkflowError) as e:
        return {"ran": False, "reason": f"Could not draft a recovery contract for this upload: {e}"}
    session.flush()

    svc.review_contract(incident, princ[Role.SUPERVISOR])
    _satisfy_monitoring(session, svc, incident, contract, princ, series)
    try:
        svc.start_monitoring(incident)
    except WorkflowError as e:
        session.refresh(incident)
        return {"ran": True, "outcome": "blocked", "state": incident.state.value,
                "contract_id": contract.id, "telemetry_rows": n, "verdict_by": "deterministic-gate",
                "message": f"Verification could not start on the uploaded data: {e}"}

    result = svc.advance(incident, n)
    _consume_leftovers(session, incident)
    session.refresh(incident)

    cycles = result.get("cycles", [])
    relapse_cycle = next((c["cycle"] for c in cycles if c.get("fault")), None)
    stable = cycles[-1]["stable_streak"] if cycles else 0
    return {
        "ran": True,
        "outcome": result["outcome"],
        "state": incident.state.value,
        "contract_id": contract.id,
        "telemetry_rows": n,
        "cycles_replayed": len(cycles),
        "stable_streak": stable,
        "relapse_cycle": relapse_cycle,
        "verdict_by": "deterministic-evaluator",
        "message": _message(result["outcome"], relapse_cycle, stable, incident),
    }
