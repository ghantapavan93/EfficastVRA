"""Persisted shift handoff — a frozen snapshot of open missions the next shift inherits + acknowledges."""

from __future__ import annotations

from sqlmodel import Session, select

from app.api.intake_routes import _sample_csv
from app.auth import Principal
from app.domain.models import User
from app.services.intake_mission import create_mission_from_upload
from app.services.shift_handoff import acknowledge, build_preview, create_handoff, list_handoffs


def _princ(session: Session, username: str = "s.vega") -> Principal:
    u = session.exec(select(User).where(User.username == username)).first()
    return Principal(u.id, u.username, u.role, u.plant_id, u.tenant_id)


def test_preview_includes_an_active_mission(session: Session):
    out = create_mission_from_upload(session, "n.csv", _sample_csv())  # active: INTERVENTION_RECORDED
    p = _princ(session)
    prev = build_preview(session, p.plant_id)
    snap = next((s for s in prev["open_missions"] if s["id"] == out["incident_id"]), None)
    assert snap is not None
    assert snap["who_next"] and "what_blocks" in snap and snap["state"]
    assert prev["stats"]["open_missions"] >= 1 and prev["headline"]


def test_create_lists_and_acknowledge(session: Session):
    create_mission_from_upload(session, "n.csv", _sample_csv())
    p = _princ(session, "s.vega")
    h = create_handoff(session, p, from_shift="A", to_shift="B", notes="watch the uploaded F27 line")
    assert h["from_shift"] == "A" and h["to_shift"] == "B"
    assert h["acknowledged_by"] is None
    assert h["stats"]["open_missions"] == len(h["open_missions"])  # snapshot is internally consistent

    assert any(x["id"] == h["id"] for x in list_handoffs(session, p.plant_id)["handoffs"])

    acked = acknowledge(session, h["id"], _princ(session, "a.lang"))
    assert acked["acknowledged_by"] == "a.lang"
    # acknowledging again keeps the first acker (receipt is recorded once)
    again = acknowledge(session, h["id"], _princ(session, "q.idris"))
    assert again["acknowledged_by"] == "a.lang"
