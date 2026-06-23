"""Counterfactual contract-calibration tests (Phase 27).

Replays the deterministic verifier over the real relapse trajectory at different verification-window
lengths. The key property: any window shorter than the cycle-17 relapse would have FALSE-CLOSED, and the
30-cycle contract is safely past it. Advisory / read-only.
"""

from __future__ import annotations

from app.domain.models import Incident
from app.seed.northstar import IDS
from app.services.sensitivity import analyze
from tests.helpers import to_monitoring, to_reopened


def test_short_windows_would_false_close_before_the_cycle_17_relapse(session):
    svc, inc = to_reopened(session)  # drives window-1 through the cycle-17 relapse + reopen
    s = analyze(session, inc)

    assert s["available"] is True
    assert s["relapse_cycle"] == 17
    assert s["min_safe_window"] == 17           # you must verify at least to the relapse cycle to catch it
    assert s["actual_required_stable_cycles"] == 30
    assert s["margin_cycles"] == 13 and s["safe"] is True

    by_k = {row["required_stable_cycles"]: row for row in s["sweep"]}
    # Anything reachable before cycle 17 would have declared a false recovery…
    assert by_k[5]["outcome"] == "false_close" and by_k[5]["close_cycle"] == 5
    assert by_k[15]["outcome"] == "false_close"
    # …and any window at/after the relapse cycle catches it instead.
    assert by_k[20]["outcome"] == "caught_relapse" and by_k[20]["close_cycle"] is None
    assert by_k[30]["outcome"] == "caught_relapse" and by_k[30]["is_contract"] is True
    assert "FALSE recovery" in s["verdict"]


def test_clean_window_cannot_be_stress_tested(session):
    # Before any relapse, the trajectory has no recurrence to calibrate against — reported honestly.
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 10)  # 10 clean cycles, no fault yet
    s = analyze(session, inc)
    assert s["available"] is True and s["relapse_cycle"] is None
    assert s["min_safe_window"] is None and s["max_stable_streak"] == 10
    assert "cannot be stress-tested" in s["verdict"]


def test_sensitivity_unavailable_before_monitoring(session):
    inc = session.get(Incident, IDS["incident"])  # raw seed: no window yet
    assert analyze(session, inc)["available"] is False
