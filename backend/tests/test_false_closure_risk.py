"""False-Closure Risk Score — an explainable, advisory pre-closure risk read.
Low for a genuine verified recovery; elevated mid-window while the precursor climbs; unavailable
before a contract exists. Read-only (never gates closure)."""

from __future__ import annotations

from app.domain.models import Incident
from app.seed.northstar import IDS
from app.services.false_closure_risk import assess_false_closure_risk
from app.workflow.demo import run_scenario
from tests.helpers import to_monitoring


def test_fcrs_low_for_a_verified_recovery(session):
    run_scenario(session, log=lambda *a: None)
    inc = session.get(Incident, IDS["incident"])
    r = assess_false_closure_risk(session, inc)
    assert r["available"] is True
    assert r["band"] == "low" and r["risk"] < 0.25
    assert r["quality_released"] is True
    assert r["factors"]                                  # explainable — per-factor contributions
    assert abs(sum(f["contribution"] for f in r["factors"]) - r["risk"]) < 0.01  # no fault override


def test_fcrs_elevated_mid_window_before_relapse(session):
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 14)                                  # cycles 1–14: precursor climbing, fault not yet fired
    r = assess_false_closure_risk(session, inc)
    assert r["available"] is True
    assert r["risk"] >= 0.25 and r["band"] in ("elevated", "high")
    assert r["fault_in_window"] is False                 # the risk is predictive, before the cycle-17 relapse
    assert r["dominant_driver"]


def test_fcrs_unavailable_before_a_contract(session):
    inc = session.get(Incident, IDS["incident"])         # seeded, no contract drafted yet
    assert assess_false_closure_risk(session, inc)["available"] is False
