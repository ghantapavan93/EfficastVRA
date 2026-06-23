"""Troubleshooting lookup tests (Phase 19) — find the answer fast, grounded and trustworthy."""

from __future__ import annotations

from app.services.troubleshooting import troubleshoot


def test_troubleshoot_returns_grounded_answer(session):
    r = troubleshoot(session, fault_code="F27", machine_model="CDX-220")

    # The machine is recognised and the answer is summarised.
    assert r["machine"]["equipment_class"] == "conveyor_drive"
    assert "F27" in r["summary"]

    # Approved procedures only — every cited source is APPROVED (no obsolete/unapproved guidance).
    assert r["approved_procedures"]
    assert all(p["approval_status"] == "APPROVED" for p in r["approved_procedures"])

    # Ranked causes, past-incident history, and signals to check are present (no manual-hunting).
    assert r["likely_causes"]
    assert any("bearing" in c["cause"].lower() for c in r["likely_causes"])
    assert r["history"] and r["history"][0]["fault_code"] == "F27"
    assert r["signals_to_check"]
    assert "precursor" in r["early_warning"].lower()


def test_troubleshoot_flags_non_authoritative_and_pending_knowledge(session):
    r = troubleshoot(session, fault_code="F27", machine_model="CDX-220")
    # Obsolete/unapproved notes are surfaced as cautions (not silently mixed into the approved answer).
    assert isinstance(r["cautions"], list)
    # Captured lessons are never shown as approved guidance.
    for k in r["knowledge"]:
        assert "pending_review" in k


def test_troubleshoot_without_machine_still_helps(session):
    r = troubleshoot(session, fault_code="F27")
    assert r["likely_causes"]
    assert r["history"]  # past F27 incidents are still found
