"""Workflow guard tests (covers required tests 5, 6, 19)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlmodel import Session

from app.domain.base import utcnow
from app.domain.enums import EvidenceStatus, WorkflowState
from app.domain.models import Incident
from app.seed.northstar import IDS
from app.workflow.recovery_service import RecoveryService, WorkflowError
from helpers import appr_id, principal, req_id, to_window2_stable


# ── Test 5: missing evidence prevents monitoring ──────────────────────────────
def test_missing_evidence_prevents_monitoring(session: Session):
    svc = RecoveryService(session)
    inc = session.get(Incident, IDS["incident"])
    sup = principal(session, "s.vega")
    c1 = svc.draft_contract(inc)
    svc.review_contract(inc, sup)
    # Approve the contract but submit NO evidence.
    svc.record_approval(inc, sup, requirement_id=appr_id(session, c1.id, "contract_review"))
    with pytest.raises(WorkflowError) as ei:
        svc.start_monitoring(inc)
    assert ei.value.code == "missing_evidence"
    assert inc.state != WorkflowState.MONITORING_RECOVERY


# ── Test 6: stale telemetry cannot satisfy a condition ────────────────────────
def test_stale_evidence_is_invalid(session: Session):
    svc = RecoveryService(session)
    inc = session.get(Incident, IDS["incident"])
    sup = principal(session, "s.vega")
    tech = principal(session, "a.lang")
    c1 = svc.draft_contract(inc)
    svc.review_contract(inc, sup)
    # Submit a post-alignment measurement whose timestamp is 3 hours old (freshness_max is 7200s).
    stale_ts = utcnow() - timedelta(hours=3)
    out = svc.submit_evidence(inc, tech,
                              requirement_id=req_id(session, c1.id, "post_alignment_measurement"),
                              value_num=3.6, unit="mm/s", evidence_timestamp=stale_ts)
    assert out.ok is False
    assert out.data["status"] == EvidenceStatus.EXPIRED.value
    svc.record_approval(inc, sup, requirement_id=appr_id(session, c1.id, "contract_review"))
    # Stale evidence does not satisfy the requirement, so monitoring is still blocked.
    with pytest.raises(WorkflowError):
        svc.start_monitoring(inc)


# ── Test 19: recovery cannot close from a technician completion alone ──────────
def test_recovery_not_closed_by_completion_alone(session: Session):
    # 30 stable cycles + completed technician work, but NO quality release.
    svc, inc, _c2 = to_window2_stable(session, cycles=30)
    result = svc.current_evaluation(inc)
    assert result.stable_streak == 30
    assert result.verdict != "verified"        # technician completion is not proof of recovery
    assert inc.state == WorkflowState.MONITORING_RECOVERY
    with pytest.raises(WorkflowError):
        svc.finalize(inc)                        # cannot finalize without quality release
