"""Decision Intelligence tests (Phase 20) — risk-adjusted economics + FMEA. Advisory, never decides."""

from __future__ import annotations

from app.services.decision import decide
from tests.helpers import to_monitoring


def test_decision_recommends_lowest_expected_cost_at_high_relapse_risk(session):
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 14)  # mid window-1: the Forecaster reports a high relapse probability

    d = decide(session, inc)
    assert d["available"] and d["p_relapse"] >= 0.6 and d["forecast_state"] == "live"

    # Cost exposure is quantified from the production order.
    assert d["impact"]["units_remaining"] == 8420
    assert d["impact"]["false_closure_exposure_usd"] > 0

    # Three risk-adjusted options, each with an expected cost; exactly one recommended (the cheapest).
    options = {o["action"]: o for o in d["options"]}
    assert set(options) == {"close_now", "keep_monitoring", "pre_stage_contingency"}
    cheapest = min(d["options"], key=lambda o: o["expected_cost_usd"])
    assert cheapest.get("recommended") is True
    # At high relapse risk, pre-staging the contingency is the lowest-expected-cost call.
    assert d["recommendation"]["action"] == "pre_stage_contingency"

    # FMEA: RPN = S×O×D, ranked high→low, and the agent's detection lowers RPN vs flying blind.
    fmea = d["fmea"]
    assert fmea and all(m["rpn"] == m["severity"] * m["occurrence"] * m["detection"] for m in fmea)
    assert fmea == sorted(fmea, key=lambda m: m["rpn"], reverse=True)
    assert all(m["rpn"] < m["rpn_without_agent"] for m in fmea)

    # It is advisory.
    assert "Advisory only" in d["advisory"]


def test_decision_costs_scale_with_relapse_risk_and_recommend_argmin(session):
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 1)                       # early → low relapse probability
    low = decide(session, inc)
    svc.advance(inc, 13)                      # cycle 14 → high relapse probability
    high = decide(session, inc)
    assert high["p_relapse"] > low["p_relapse"]

    # The recommendation is always the minimum-expected-cost option (a real argmin, not "any of three").
    for d in (low, high):
        cheapest = min(d["options"], key=lambda o: o["expected_cost_usd"])["action"]
        assert d["recommendation"]["action"] == cheapest

    # Expected costs are genuinely risk-scaled: every option is cheaper at low risk than at high risk.
    lo = {o["action"]: o["expected_cost_usd"] for o in low["options"]}
    hi = {o["action"]: o["expected_cost_usd"] for o in high["options"]}
    assert all(lo[a] < hi[a] for a in ("close_now", "keep_monitoring", "pre_stage_contingency"))
    # close_now is risk-discounted below the undiscounted false-closure exposure (p < 1).
    assert lo["close_now"] < low["impact"]["false_closure_exposure_usd"]
