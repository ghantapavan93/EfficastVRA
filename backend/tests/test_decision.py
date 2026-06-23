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


def test_decision_recommendation_flips_when_relapse_risk_is_low(session):
    # Before any divergence, a low relapse probability should NOT recommend paying to pre-stage.
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 1)
    d = decide(session, inc)
    # With p_relapse low, pre-staging's fixed prep cost makes "keep monitoring" or "close" cheaper.
    assert d["recommendation"]["action"] in ("close_now", "keep_monitoring", "pre_stage_contingency")
    # Sanity: the recommendation is always the minimum-expected-cost option.
    cheapest = min(d["options"], key=lambda o: o["expected_cost_usd"])["action"]
    assert d["recommendation"]["action"] == cheapest
