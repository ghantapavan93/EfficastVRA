"""Recovery Passport (per-asset history) + Recovery Twin (scrubbable trajectory) — read-only projections."""

from __future__ import annotations

from sqlmodel import Session

from app.api.intake_routes import _sample_csv
from app.domain.models import Incident
from app.services.intake_mission import create_mission_from_upload
from app.services.recovery_passport import build_passport, list_assets
from app.services.recovery_twin import build_twin
from app.services.uploaded_verification import run_uploaded_verification


def _upload(session: Session) -> Incident:
    out = create_mission_from_upload(session, "northstar.csv", _sample_csv())
    return session.get(Incident, out["incident_id"])


def test_list_assets_includes_the_machine(session: Session):
    inc = _upload(session)
    assets = list_assets(session)["assets"]
    assert any(a["id"] == inc.machine_id and a["mission_count"] >= 1 for a in assets)


def test_passport_counts_the_uploaded_false_closure(session: Session):
    inc = _upload(session)
    p = build_passport(session, inc.machine_id)
    assert p["available"] is True
    entry = next(e for e in p["entries"] if e["id"] == inc.id)
    assert entry["from_upload"] is True
    assert entry["false_closure_caught"] is True          # reconstruction flagged the relapse
    assert p["stats"]["false_closures_caught"] >= 1
    assert len(p["entries"]) == p["stats"]["total_missions"]


def test_twin_unavailable_before_a_contract(session: Session):
    inc = _upload(session)
    twin = build_twin(session, inc)
    assert twin["available"] is False


def test_twin_replays_the_relapse(session: Session):
    inc = _upload(session)
    run_uploaded_verification(session, inc)
    twin = build_twin(session, inc)
    assert twin["available"] is True
    assert len(twin["frames"]) >= 17
    assert any(f["stable_streak"] == 16 for f in twin["frames"])   # streak built, then...
    f17 = next(f for f in twin["frames"] if f["cycle"] == 17)
    assert f17["fault_code"] == "F27" and f17["stable_streak"] == 0  # ...reset by the relapse
    relapse = [m for m in twin["markers"] if m["kind"] == "relapse"]
    assert relapse and relapse[0]["cycle"] == 17
