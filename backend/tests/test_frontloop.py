"""Front-of-loop tests (Phase 9): MAIA alert → agent triage → human accepts → existing flow.

Proves the agent *proposes* a diagnosis/intervention from a real alert, that a human (supervisor) —
not the agent, not a technician — must accept it, and that acceptance hands cleanly to the existing
Recovery Contract flow. The agent never performs physical work or accepts its own diagnosis.
"""

from __future__ import annotations

import pytest
from sqlmodel import select

from app.agent.trace import list_traces
from app.domain.enums import InterventionStatus, WorkflowState
from app.domain.models import Incident, Intervention, MaiaAlert
from app.workflow.recovery_service import RecoveryService, WorkflowError
from app.workflow.state_machine import StateError
from tests.helpers import principal


def _open_alert(svc: RecoveryService):
    alerts = svc.port.get_open_alerts()
    assert alerts, "seed should provide an open MAIA alert"
    return alerts[0]


def test_triage_creates_proposed_intervention_with_reasoning(session):
    svc = RecoveryService(session)
    alert = _open_alert(svc)
    inc = svc.triage_from_alert(alert)

    assert inc.state == WorkflowState.INTERVENTION_PROPOSED
    assert inc.origin_alert_id == alert.id
    itv = session.exec(select(Intervention).where(Intervention.incident_id == inc.id)).first()
    assert itv is not None and itv.status == InterventionStatus.PROPOSED
    assert itv.kind == "coupling_alignment"

    nodes = [t.node for t in list_traces(session, inc.id)]
    for n in ("perceive", "classify", "retrieve", "hypothesize", "propose"):
        assert n in nodes, f"triage missing reasoning node {n}"

    # the alert is now triaged and linked to the incident
    alert_row = session.get(MaiaAlert, alert.id)
    assert alert_row.status == "triaged" and alert_row.resulted_in_incident == inc.id


def test_triage_is_idempotent_per_alert(session):
    svc = RecoveryService(session)
    alert = _open_alert(svc)
    a = svc.triage_from_alert(alert)
    b = svc.triage_from_alert(alert)
    assert a.id == b.id
    incidents = session.exec(select(Incident).where(Incident.origin_alert_id == alert.id)).all()
    assert len(incidents) == 1


def test_technician_cannot_accept_diagnosis(session):
    svc = RecoveryService(session)
    inc = svc.triage_from_alert(_open_alert(svc))
    tech = principal(session, "a.lang")
    with pytest.raises(StateError):
        svc.accept_diagnosis(inc, tech)
    session.refresh(inc)
    assert inc.state == WorkflowState.INTERVENTION_PROPOSED  # unchanged


def test_supervisor_accept_records_intervention_and_hands_off(session):
    svc = RecoveryService(session)
    inc = svc.triage_from_alert(_open_alert(svc))
    sup = principal(session, "s.vega")
    svc.accept_diagnosis(inc, sup)
    session.refresh(inc)
    assert inc.state == WorkflowState.INTERVENTION_RECORDED
    itv = session.exec(select(Intervention).where(Intervention.incident_id == inc.id)).first()
    assert itv.status == InterventionStatus.COMPLETED and itv.technician_id

    # hands off to the existing Recovery Contract flow without modification
    contract = svc.draft_contract(inc)
    session.refresh(inc)
    assert inc.state == WorkflowState.RECOVERY_CONTRACT_DRAFTED
    assert contract.contract_no


def test_cannot_accept_before_triage(session):
    svc = RecoveryService(session)
    inc = session.get(Incident, "INC-2841")  # seeded, already at INTERVENTION_RECORDED
    sup = principal(session, "s.vega")
    with pytest.raises(WorkflowError):
        svc.accept_diagnosis(inc, sup)
