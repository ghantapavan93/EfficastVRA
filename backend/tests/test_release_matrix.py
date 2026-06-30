"""Recovery Decision Room (multi-domain release matrix) + Evidence Value Planner — both composed read-only
from the deterministic evaluator + disposition. They decide nothing; they re-project + rank.
"""

from __future__ import annotations

from sqlmodel import Session

from app.domain.models import Incident
from app.seed.northstar import IDS
from app.services.evidence_planner import plan_evidence
from app.services.release_matrix import assess_release_matrix
from tests.helpers import to_quality_released, to_window2_stable

_DOMAINS = {"Equipment", "Process", "Quality", "Comparability", "Evidence", "Freshness", "Safety", "Authorization"}


def test_release_matrix_has_all_eight_domains(session: Session):
    _svc, inc, _c = to_window2_stable(session, cycles=30)
    m = assess_release_matrix(session, inc)
    assert m["available"]
    assert {d["domain"] for d in m["domains"]} == _DOMAINS
    safety = next(d for d in m["domains"] if d["domain"] == "Safety")
    assert safety["status"] == "pass"  # machine control prohibited — always passes


def test_release_matrix_blocks_release_without_approval(session: Session):
    _svc, inc, _c = to_window2_stable(session, cycles=30)
    m = assess_release_matrix(session, inc)
    auth = next(d for d in m["domains"] if d["domain"] == "Authorization")
    assert auth["status"] == "blocked"
    assert m["can_close"] is False
    assert m["blocking_count"] >= 1
    assert m["outcome"] != "VERIFIED"


def test_release_matrix_authorized_once_quality_released(session: Session):
    _svc, inc, _c = to_quality_released(session, cycles=30)
    m = assess_release_matrix(session, inc)
    auth = next(d for d in m["domains"] if d["domain"] == "Authorization")
    quality = next(d for d in m["domains"] if d["domain"] == "Quality")
    assert auth["status"] == "pass"
    assert quality["status"] == "pass"


def test_evidence_planner_prioritizes_quality_approval(session: Session):
    _svc, inc, _c = to_window2_stable(session, cycles=30)
    p = plan_evidence(session, inc)
    assert p["available"]
    assert any("quality approval" in r["title"].lower() for r in p["recommendations"])
    assert p["recommendations"][0]["decision_impact"] == "Critical"  # the critical unblocker ranks first
    assert p["potential_confidence"] >= p["current_confidence"]


def test_evidence_planner_unavailable_before_a_contract(session: Session):
    inc = session.get(Incident, IDS["incident"])  # fresh incident, no contract yet
    p = plan_evidence(session, inc)
    assert p["available"] is False
