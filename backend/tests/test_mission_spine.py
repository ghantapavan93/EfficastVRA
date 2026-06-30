"""Recovery Mission Spine — one incident projected onto the seven-stage mission, with where it stands,
what's blocking, who acts next, and why it isn't VERIFIED. Read-only projection; decides nothing.
"""

from __future__ import annotations

from sqlmodel import Session

from app.domain.models import Incident
from app.seed.northstar import IDS
from app.services.mission_spine import STAGES, assess_mission
from tests.helpers import to_quality_released, to_window2_stable


def test_spine_complete_when_verified(session: Session):
    _svc, inc, _c = to_quality_released(session, cycles=30)
    s = assess_mission(session, inc)
    assert s["available"]
    assert s["outcome"] == "VERIFIED"
    assert s["complete"] is True
    assert s["current_index"] == len(STAGES)
    assert all(st["status"] == "done" for st in s["stages"])
    assert "complete" in s["who_next"].lower()


def test_spine_blocks_on_quality_and_names_next_actor(session: Session):
    _svc, inc, _c = to_window2_stable(session, cycles=30)
    s = assess_mission(session, inc)
    assert s["complete"] is False
    assert "quality" in s["who_next"].lower()  # quality release is the next required human action
    assert s["why_not_verified"]
    cur = s["stages"][s["current_index"]]
    assert cur["status"] in ("active", "blocked")


def test_spine_early_needs_contract(session: Session):
    inc = session.get(Incident, IDS["incident"])  # fresh incident, no contract yet
    s = assess_mission(session, inc)
    assert s["stages"][0]["status"] == "done"  # intake always captured
    assert s["current_stage"] in ("Recovery Contract", "Reconstruction")
    assert "contract" in s["who_next"].lower()
