"""Intake → live mission: an uploaded export becomes a real, persisted Incident (with its intake analysis
attached + a reusable Mapping Profile), appears in the missions list, and reads correctly in the spine.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.api.intake_routes import _sample_csv
from app.api.serializers import mission_summary
from app.domain.models import Incident, MappingProfile
from app.services.intake_mission import create_mission_from_upload
from app.services.mission_spine import assess_mission


def test_create_mission_persists_incident_with_intake(session: Session):
    out = create_mission_from_upload(session, "north.csv", _sample_csv())
    assert out["created"] is True
    inc = session.get(Incident, out["incident_id"])
    assert inc is not None
    assert inc.intake and inc.intake.get("reconstruction")  # analysis stored on the incident
    assert inc.fault_code == "F27"
    assert out["false_closure_detected"] is True
    assert any(p.id == out["mapping_profile_id"] for p in session.exec(select(MappingProfile)).all())


def test_created_mission_reads_in_the_spine(session: Session):
    out = create_mission_from_upload(session, "north.csv", _sample_csv())
    s = assess_mission(session, session.get(Incident, out["incident_id"]))
    assert s["available"]
    assert s["stages"][0]["status"] == "done"   # Intake captured
    assert s["stages"][1]["status"] == "done"   # Reconstruction (from the upload)
    assert s["current_stage"] == "Recovery Contract"
    assert "contract" in s["who_next"].lower()


def test_created_mission_serializes_in_missions_list(session: Session):
    out = create_mission_from_upload(session, "north.csv", _sample_csv())
    ms = mission_summary(session, session.get(Incident, out["incident_id"]))
    assert ms["id"] == out["incident_id"]
    assert ms["fault_code"] == "F27"
    assert ms["is_active"] is True
