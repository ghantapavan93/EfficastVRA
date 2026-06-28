"""Lot-at-Risk — flags the questionable production window after a fault; read-only (never auto-disposition)."""

from __future__ import annotations

from app.services.lot_at_risk import assess_lot_at_risk
from tests.helpers import to_monitoring, to_reopened


def test_lot_at_risk_flags_the_questionable_window(session):
    _svc, inc = to_reopened(session)   # F27 recurs during the window
    r = assess_lot_at_risk(session, inc)
    assert r["at_risk"] is True
    assert r["fault_code"] == "F27"
    assert r["first_questionable_cycle"] is not None
    assert r["last_good_cycle"] == r["first_questionable_cycle"] - 1   # the cycle just before the fault
    assert r["affected_window"]["from"] and r["affected_window"]["to"]
    assert "Material Review Board" in r["required_quality_action"]     # a recommendation, not an action


def test_lot_at_risk_none_when_no_fault(session):
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 5)   # clean cycles, no fault
    assert assess_lot_at_risk(session, inc)["at_risk"] is False
