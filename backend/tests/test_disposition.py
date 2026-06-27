"""Recovery Disposition — the four-outcome decision made explicit + the hard closure invariants.
The headline property: telemetry looking recovered NEVER closes on its own — the quality/evidence/approval
invariants are mandatory (a low risk score cannot substitute). Read-only; the evaluator owns closure."""

from __future__ import annotations

from app.domain.models import Incident
from app.seed.northstar import IDS
from app.services.disposition import assess_disposition
from app.workflow.demo import run_scenario
from tests.helpers import to_monitoring, to_window2_stable


def test_disposition_verified_for_full_recovery(session):
    run_scenario(session, log=lambda *a: None)
    inc = session.get(Incident, IDS["incident"])
    d = assess_disposition(session, inc)
    assert d["available"] is True
    assert d["disposition"] == "VERIFIED" and d["can_close"] is True and d["decided"] is True
    assert all(inv["ok"] for inv in d["hard_invariants"])            # every hard invariant satisfied
    assert d["human_status"]["telemetry"] == "stable"
    assert d["human_status"]["quality"] == "released"
    assert d["conflict"] is False


def test_disposition_insufficient_when_telemetry_ok_but_quality_missing(session):
    # 30 stable cycles on the bearing contract, but quality release NOT granted — the reviewer's exact case:
    # telemetry looks recovered, the closure gate is not met → the system refuses false certainty.
    _svc, inc, _c2 = to_window2_stable(session, cycles=30)
    d = assess_disposition(session, inc)
    assert d["disposition"] == "INSUFFICIENT_EVIDENCE"
    assert d["can_close"] is False                                   # cannot close despite good telemetry
    inv = {i["key"]: i["ok"] for i in d["hard_invariants"]}
    assert inv["window"] is True and inv["machine"] is True          # machine side complete
    assert inv["approvals"] is False                                 # quality release missing → mandatory gate fails
    assert d["human_status"]["telemetry"] == "stable"
    assert d["human_status"]["quality"] == "pending"


def test_disposition_in_progress_mid_window(session):
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 10)                                             # cycles 1–10, before the relapse
    d = assess_disposition(session, inc)
    assert d["disposition"] == "IN_PROGRESS" and d["can_close"] is False
    assert {i["key"]: i["ok"] for i in d["hard_invariants"]}["window"] is False


def test_disposition_unavailable_before_a_contract(session):
    inc = session.get(Incident, IDS["incident"])
    assert assess_disposition(session, inc)["available"] is False
