"""Governance posture tests (Phase 17) — the controls are real, live, and honestly reported."""

from __future__ import annotations

from app.services.governance import posture
from app.workflow.demo import run_scenario


def test_posture_reports_security_logging_and_auditability(session):
    run_scenario(session, log=lambda *a: None)
    p = posture(session)

    # Security is present and concrete.
    sec = p["security"]
    assert "machine_start" in sec["prohibited_actions"]
    assert set(sec["roles"]) == {"supervisor", "technician", "quality_engineer", "plant_admin"}
    assert "server-authoritative" in sec["authorization"]

    # Logging is present.
    assert p["logging"]["correlation_ids"]
    assert "JSON" in p["logging"]["format"]

    # Auditability is present AND verified live (tamper-evident hash chain intact).
    aud = p["auditability"]
    assert aud["tamper_evident"].startswith("per-correlation")
    assert aud["live_integrity"]["checked"] is True
    assert aud["live_integrity"]["intact"] is True
    assert aud["live_integrity"]["entries"] > 0

    # Enterprise control-framework alignment is mapped.
    frameworks = {c["framework"].split(" ")[0] for c in p["control_alignment"]}
    assert {"IEC", "ISO/IEC", "SOC", "NIST"} <= frameworks

    # Honesty: real enterprise gaps are disclosed, not hidden.
    assert any("SSO" in g or "OIDC" in g for g in p["honest_gaps"])
