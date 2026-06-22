"""Phase-2 core: cycle engine + evaluator + reopening (the cycle-17 branch)."""

from __future__ import annotations

from sqlmodel import Session, select

from app.adapters.synthetic import SyntheticEfficastPort
from app.domain.enums import InterventionStatus, Role, WorkflowState
from app.domain.models import Incident, Intervention, Machine, RecoveryContract
from app.seed.northstar import IDS
from app.services.contract_templates import build_v1_spec
from app.services.cycle_engine import advance_cycle
from app.services.policy import should_reopen
from app.services.windows import open_window
from app.workflow.contract_builder import persist_contract
from app.workflow.reopening import reopen_with_contingency
from app.workflow.state_machine import transition


def _start_v1_monitoring(session: Session) -> tuple[Incident, RecoveryContract]:
    incident = session.get(Incident, IDS["incident"])
    machine = session.get(Machine, IDS["machine"])
    spec = build_v1_spec(incident.id, IDS["intervention_1"], IDS["contract_no"])
    contract = persist_contract(session, incident, spec)
    contract.status = "active"
    session.add(contract)
    open_window(session, incident_id=incident.id, contract=contract, sequence=1,
                required_stable_cycles=30, baseline=machine.baseline)
    # Walk the state machine to MONITORING_RECOVERY with role-appropriate actors.
    transition(session, incident, WorkflowState.RECOVERY_CONTRACT_DRAFTED, actor="agent", role=Role.AGENT, reason="draft")
    transition(session, incident, WorkflowState.RECOVERY_CONTRACT_REVIEWED, actor="s.vega", role=Role.SUPERVISOR, reason="review")
    transition(session, incident, WorkflowState.AWAITING_REQUIRED_EVIDENCE, actor="agent", role=Role.AGENT, reason="await")
    transition(session, incident, WorkflowState.READY_FOR_MONITORING, actor="system", role=Role.SYSTEM, reason="ready")
    transition(session, incident, WorkflowState.MONITORING_RECOVERY, actor="system", role=Role.SYSTEM, reason="start")
    session.flush()
    return incident, contract


def test_sixteen_cycles_look_like_recovery(session: Session):
    _incident, contract = _start_v1_monitoring(session)
    port = SyntheticEfficastPort(session)
    result = None
    for _ in range(16):
        _obs, result = advance_cycle(session, port, contract)
    assert result is not None
    assert result.verdict == "monitoring"
    assert result.stable_streak == 16
    assert "fault_f27" not in result.violated_keys


def test_cycle_17_violates_and_reopens(session: Session):
    incident, contract = _start_v1_monitoring(session)
    port = SyntheticEfficastPort(session)
    result = None
    for _ in range(17):
        _obs, result = advance_cycle(session, port, contract)

    # Cycle 17: F27 recurs -> violation.
    assert result.verdict == "violated"
    assert "fault_f27" in result.violated_keys
    assert result.stable_streak == 0
    assert should_reopen(contract, result) is True

    v2 = reopen_with_contingency(
        session, port, incident, contract, violated_keys=result.violated_keys,
    )
    session.refresh(incident)
    session.refresh(contract)

    # Incident reopened and parked for contingency approval.
    assert incident.state == WorkflowState.CONTINGENCY_AWAITING_APPROVAL
    assert incident.reopened_count == 1
    assert incident.current_contract_id == v2.id

    # First intervention + contract preserved in history.
    assert contract.status == "violated"
    assert contract.superseded_by == v2.id
    itv1 = session.get(Intervention, IDS["intervention_1"])
    assert itv1.status == InterventionStatus.COMPLETED  # not deleted, not altered

    # Contingency intervention exists (bearing replacement, sequence 2).
    contingency = session.exec(
        select(Intervention).where(Intervention.incident_id == incident.id).where(Intervention.sequence == 2)
    ).first()
    assert contingency is not None
    assert contingency.kind == "bearing_replacement"
    assert v2.version == 2


def test_thirty_stable_cycles_required_window2(session: Session):
    """In the second window the machine is stable, but verification still needs 30 cycles AND
    quality release — so it must not read 'verified' at 29 cycles or without quality evidence."""
    incident, contract = _start_v1_monitoring(session)
    port = SyntheticEfficastPort(session)
    for _ in range(17):
        _obs, result = advance_cycle(session, port, contract)
    v2 = reopen_with_contingency(session, port, incident, contract, violated_keys=result.violated_keys)
    v2.status = "active"
    session.add(v2)
    machine = session.get(Machine, IDS["machine"])
    open_window(session, incident_id=incident.id, contract=v2, sequence=2,
                required_stable_cycles=30, baseline=machine.baseline)

    result = None
    for _ in range(29):
        _obs, result = advance_cycle(session, port, v2)
    assert result.stable_streak == 29
    assert result.verdict != "verified"  # 29 < 30

    _obs, result = advance_cycle(session, port, v2)
    assert result.stable_streak == 30
    # 30 stable cycles, but no first-piece evidence + no quality release => still not verified.
    assert result.verdict != "verified"
    assert result.awaiting_quality is False  # blocked earlier on first_piece evidence, not quality-only
