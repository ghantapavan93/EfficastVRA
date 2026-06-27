"""Recovery Certificate — the third primitive (proof of recovery). Composed read-only from the
deterministic verdict + provenance + signature; deterministic; only meaningful once a contract exists."""

from __future__ import annotations

from app.domain.models import Incident
from app.seed.northstar import IDS
from app.services.certificate import build_certificate
from app.workflow.demo import run_scenario


def test_certificate_for_a_verified_recovery(session):
    run_scenario(session, log=lambda *a: None)
    inc = session.get(Incident, IDS["incident"])
    cert = build_certificate(session, inc)
    assert cert["available"] is True
    assert cert["status"] == "certified"
    assert cert["verdict"] == "VERIFIED_RECOVERY"
    assert cert["certificate_id"].startswith("RSC-")
    assert cert["audit"]["intact"] is True and cert["audit"]["head_hash"]
    assert cert["conditions"] and cert["approvals"]          # deterministic conditions + human signatures
    assert cert["trustworthy"] is True
    assert cert["signature"]["rung"]                          # intervention-consistency carried
    assert cert["subject"]["fault_code"] == inc.fault_code   # machine-agnostic, derived
    assert len(cert["certificate_hash"]) == 64               # sha256 hex


def test_certificate_is_deterministic(session):
    run_scenario(session, log=lambda *a: None)
    inc = session.get(Incident, IDS["incident"])
    a = build_certificate(session, inc)
    b = build_certificate(session, inc)
    assert a["certificate_hash"] == b["certificate_hash"]
    assert a["audit"]["head_hash"] == b["audit"]["head_hash"]


def test_certificate_unavailable_before_a_contract(session):
    inc = session.get(Incident, IDS["incident"])  # seeded at INTERVENTION_RECORDED, no contract yet
    cert = build_certificate(session, inc)
    assert cert["available"] is False
