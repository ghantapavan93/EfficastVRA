"""Knowledge review & learning-loop tests (Phase 21) — human-curated institutional memory."""

from __future__ import annotations

import pytest

from app.domain.enums import KnowledgeStatus
from app.services.knowledge import list_candidates, review_knowledge
from app.services.troubleshooting import troubleshoot
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
