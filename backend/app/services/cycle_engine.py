"""Cycle engine: ingest the next post-intervention telemetry sample into a verification window.

In synthetic mode the sample comes from :class:`ScenarioPhysics`; in a real deployment it would be a
reading streamed from Efficast Edge. Either way the engine persists a :class:`RecoveryObservation`,
refreshes the machine's cached live readings, updates the consecutive-stable-cycle streak, and
returns a fresh deterministic evaluation.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.adapters.efficast_port import EfficastPort
from app.domain.base import utcnow
from app.domain.models import (
    Machine,
    RecoveryCondition,
    RecoveryContract,
    RecoveryObservation,
)
from app.services.evaluator import EvaluationResult, evaluate, is_stable_observation
from app.services.telemetry import resolve_source
from app.services.windows import get_active_window

# Sample keys promoted to first-class observation columns; anything else (a machine-class signal such
# as melt_temperature / injection_pressure / oil_temperature) is carried in obs.raw, where the
# evaluator's signal_value() resolves it. This is what lets a press/pump stream verify through the
# same engine as the conveyor.
_STANDARD_SAMPLE_KEYS = {
    "vibration", "temperature", "cycle_time", "scrap_pct", "fault_code", "bearing_precursor",
}


def advance_cycle(
    session: Session,
    port: EfficastPort,
    contract: RecoveryContract,
) -> tuple[RecoveryObservation, EvaluationResult]:
    window = get_active_window(session, contract)
    if window is None:
        raise RuntimeError("no active verification window — start monitoring first")

    next_index = window.observed_cycles + 1
    machine_id = contract_machine_id(session, contract)
    # Prefer real ingested telemetry when present for this machine; otherwise the synthetic plant.
    source = resolve_source(session, port, machine_id)
    sample = source.next_sample(
        machine_id=machine_id, window_seq=window.sequence, cycle_index=next_index,
        baseline=window.baseline or {},
    )
    # Honest provenance: stamp the *actual* source + freshness of this sample (ingested data is no
    # longer mislabelled "SyntheticEfficastPort" with a fictional 2 s age).
    src_label, src_freshness = source.provenance()
    # Machine-class signals beyond the standard columns travel in obs.raw for the evaluator to read.
    extra_signals = {k: v for k, v in sample.items() if k not in _STANDARD_SAMPLE_KEYS}

    obs = RecoveryObservation(
        tenant_id=contract.tenant_id,
        incident_id=contract.incident_id,
        contract_id=contract.id,
        window_id=window.id,
        cycle_index=next_index,
        at=utcnow(),
        vibration=sample.get("vibration"),
        temperature=sample.get("temperature"),
        cycle_time=sample.get("cycle_time"),
        scrap_pct=sample.get("scrap_pct"),
        fault_code=sample.get("fault_code"),
        bearing_precursor=sample.get("bearing_precursor"),
        source=src_label,
        freshness_s=src_freshness,
        raw=extra_signals,
    )
    session.add(obs)

    # Refresh the machine's cached live readings (what get_machine_snapshot returns).
    machine = session.get(Machine, machine_id)
    if machine is not None:
        machine.live = {
            "vibration": sample.get("vibration"),
            "temperature": sample.get("temperature"),
            "cycle_time": sample.get("cycle_time"),
            "scrap_pct": sample.get("scrap_pct"),
            "fault_code": sample.get("fault_code"),
            "at": obs.at.isoformat(),
            "freshness_s": src_freshness,
        }
        session.add(machine)

    # Update stable-cycle streak.
    conditions = session.exec(
        select(RecoveryCondition).where(RecoveryCondition.contract_id == contract.id)
    ).all()
    window.observed_cycles = next_index
    window.status = "monitoring"
    if window.started_at is None:
        window.started_at = obs.at
    if is_stable_observation(obs, conditions):
        window.stable_streak += 1
    else:
        window.stable_streak = 0
    session.add(window)
    session.flush()

    result = evaluate(session, contract)
    return obs, result


def contract_machine_id(session: Session, contract: RecoveryContract) -> str:
    from app.domain.models import Incident

    incident = session.get(Incident, contract.incident_id)
    return incident.machine_id if incident else ""
