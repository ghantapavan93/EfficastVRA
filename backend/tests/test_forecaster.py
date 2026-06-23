"""Recovery Forecaster tests (Phase 16) — the novel primitive.

Proves the forecaster predicts a false recovery *before* the originating fault fires (from the hidden
bearing precursor), and stays confident for a genuine recovery. It is advisory — these tests check the
prediction, not any state change (the deterministic evaluator still owns closure/reopen).
"""

from __future__ import annotations

from app.services.forecaster import forecast
from tests.helpers import to_monitoring, to_window2_stable


def test_forecaster_predicts_relapse_before_the_fault_fires(session):
    svc, inc, c1 = to_monitoring(session)
    svc.advance(inc, 16)  # cycles 1-16; the F27 relapse is at cycle 17 — not yet fired

    f = forecast(session, c1)
    assert f.available
    assert f.fault_cycle is None  # the fault has NOT recurred yet ...
    assert f.predicted_relapse_cycle is not None  # ... but the forecaster already saw it coming
    assert 0 < f.predicted_relapse_cycle < 17
    assert f.p_relapse >= 0.6
    h2 = next(h for h in f.hypotheses if h["id"] == "H2")
    assert h2["support"] >= 0.6
    assert "precursor" in f.leading_indicator


def test_forecaster_is_confident_for_a_genuine_recovery(session):
    svc, inc, c2 = to_window2_stable(session, cycles=12)  # post-bearing window: stable, precursor low

    f = forecast(session, c2)
    assert f.available
    assert f.predicted_relapse_cycle is None
    assert f.p_recovery_holds >= 0.8


def test_forecast_is_advisory_only_state_unchanged(session):
    # Forecasting must never change workflow state — it only reads and predicts.
    svc, inc, c1 = to_monitoring(session)
    svc.advance(inc, 10)
    state_before = inc.state
    forecast(session, c1)
    forecast(session, c1)
    session.refresh(inc)
    assert inc.state == state_before
