"""Mapping-profile reuse — a confirmed mapping pays off on the next, similar export."""

from __future__ import annotations

from sqlmodel import Session

from app.api.intake_routes import _sample_csv
from app.services.intake import analyze_upload
from app.services.intake_mission import create_mission_from_upload, get_profile_mappings, list_profiles


def test_profile_is_saved_and_listed(session: Session):
    out = create_mission_from_upload(session, "n.csv", _sample_csv())
    profs = list_profiles(session)["profiles"]
    assert any(p["id"] == out["mapping_profile_id"] and p["mapped_columns"] >= 1 for p in profs)


def test_reusing_a_profile_applies_saved_mapping(session: Session):
    first = create_mission_from_upload(session, "n.csv", _sample_csv())
    saved = get_profile_mappings(session, first["mapping_profile_id"])
    assert saved
    analysis = analyze_upload("n2.csv", _sample_csv(), saved_profile=saved)
    assert analysis["profile_applied"] is True
    assert any(m["note"] == "reused from saved profile" for m in analysis["mappings"])


def test_create_mission_with_a_reused_profile(session: Session):
    first = create_mission_from_upload(session, "n.csv", _sample_csv())
    saved = get_profile_mappings(session, first["mapping_profile_id"])
    second = create_mission_from_upload(session, "n2.csv", _sample_csv(), saved_profile=saved)
    assert second["created"] is True and second["profile_applied"] is True
    assert second["fault"] == "F27"  # the reused mapping still extracts the originating fault
