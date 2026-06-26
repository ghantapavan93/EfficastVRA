"""Knowledge review & learning-loop tests (Phase 21) — human-curated institutional memory."""

from __future__ import annotations

import pytest
from sqlmodel import select

from app.domain.enums import KnowledgeStatus
from app.domain.models import (
    Component,
    Incident,
    Intervention,
    Machine,
    RecoveryContract,
    RecoveryObservation,
)
from app.seed.northstar import IDS
from app.services.knowledge import list_candidates, review_knowledge
from app.services.troubleshooting import troubleshoot
from app.tools.registry import derive_knowledge_candidate
from app.workflow.demo import run_scenario
from app.workflow.recovery_service import WorkflowError
from tests.helpers import principal


def test_verified_recovery_creates_a_pending_candidate(session):
    run_scenario(session, log=lambda *a: None)
    cands = list_candidates(session)
    assert cands and cands[0].status == KnowledgeStatus.PENDING_REVIEW


def test_only_the_reviewer_role_can_curate(session):
    run_scenario(session, log=lambda *a: None)
    kc = list_candidates(session)[0]
    tech = principal(session, "a.lang")
    with pytest.raises(WorkflowError) as e:
        review_knowledge(session, kc.id, tech, decision="approve")
    assert e.value.status_code == 403


def test_quality_engineer_approves_and_it_becomes_authoritative(session):
    run_scenario(session, log=lambda *a: None)
    kc = list_candidates(session)[0]
    qual = principal(session, "q.idris")

    reviewed = review_knowledge(session, kc.id, qual, decision="approve", reason="generalises to CDX-220 fleet")
    assert reviewed.status == KnowledgeStatus.APPROVED
    assert reviewed.reviewed_by == "q.idris"

    # The curated lesson now surfaces in troubleshooting as no longer pending (authoritative).
    ts = troubleshoot(session, fault_code="F27", machine_model="CDX-220")
    approved = [k for k in ts["knowledge"] if not k["pending_review"]]
    assert approved, "approved lesson should appear as authoritative in troubleshooting"

    # Re-reviewing a curated candidate is rejected (idempotent guard).
    with pytest.raises(WorkflowError):
        review_knowledge(session, kc.id, qual, decision="approve")


# ── M-C: the candidate is derived from the incident, not hardcoded ────────────
def test_candidate_is_derived_from_the_incident(session):
    run_scenario(session, log=lambda *a: None)
    inc = session.get(Incident, IDS["incident"])
    kc = list_candidates(session)[0]

    machine = session.get(Machine, inc.machine_id)
    contract = session.get(RecoveryContract, inc.current_contract_id)
    success = session.get(Intervention, contract.intervention_id)
    component = session.get(Component, success.component_id)

    # Every machine-specific token traces back to a row, not a literal.
    assert kc.applicable_models == [machine.machine_model]
    assert inc.fault_code and inc.fault_code in kc.title and inc.fault_code in kc.lesson
    assert component.part_number and component.part_number in kc.lesson
    assert kc.component == component.kind
    assert kc.successful_intervention == success.id
    assert kc.conditions["required_stable_cycles"] == int(
        contract.verification_window["required_stable_cycles"])

    # The relapse cycle is read from the first faulted observation, not assumed.
    faulted = next(o for o in session.exec(
        select(RecoveryObservation).where(RecoveryObservation.incident_id == inc.id)
        .order_by(RecoveryObservation.cycle_index)).all() if o.fault_code)
    assert kc.conditions["recurrence_cycle"] == faulted.cycle_index


def test_candidate_text_tracks_a_different_machine_and_part(session):
    """Proof it is not hardcoded: change the machine model + replaced part, re-derive, and the lesson
    follows the new facts while the old Northstar literals disappear."""
    run_scenario(session, log=lambda *a: None)
    inc = session.get(Incident, IDS["incident"])
    contract = session.get(RecoveryContract, inc.current_contract_id)
    success = session.get(Intervention, contract.intervention_id)
    machine = session.get(Machine, inc.machine_id)
    component = session.get(Component, success.component_id)

    machine.machine_model = "ZX-900"
    component.part_number = "XQ-1"
    session.add(machine)
    session.add(component)
    session.flush()

    fields = derive_knowledge_candidate(session, inc)
    assert fields["applicable_models"] == ["ZX-900"]
    assert "ZX-900" in fields["lesson"]
    assert "XQ-1" in fields["lesson"]
    assert "CDX-220" not in fields["lesson"] and "BR-6205" not in fields["lesson"]
