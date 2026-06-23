"""Reliability-statistics tests (Phase 22).

The zero-failure / success-run reliability-demonstration math, and the incident assessment that grades
the verification window and reads the bathtub-curve hazard. Advisory — proven here to never change state.
"""

from __future__ import annotations

import math

from app.domain.models import Incident
from app.seed.northstar import IDS
from app.services import reliability_stats as R
from app.services.reliability_stats import (
    _relapse_history,
    assess,
    confidence_relapse_at_most,
    cycles_required,
    reliability_lower_bound,
    sprt_bounds,
    sprt_evaluate,
    survival_probability,
)
from tests.helpers import to_monitoring, to_window2_stable

_SPRT = dict(p0=0.05, p1=0.20, alpha=0.05, beta=0.05)


def test_pure_math_identities():
    # confidence that relapse ≤ p0 after n fault-free cycles is 1 − (1−p0)^n, increasing in n, 0 at n=0.
    assert confidence_relapse_at_most(0, 0.05) == 0.0
    assert math.isclose(confidence_relapse_at_most(30, 0.05), 1 - 0.95**30, rel_tol=1e-9)
    seq = [confidence_relapse_at_most(n, 0.05) for n in range(1, 40)]
    assert seq == sorted(seq) and all(0.0 < x < 1.0 for x in seq)

    # per-cycle reliability lower bound R_LCB = (1−C)^(1/n), increasing in n, in (0,1).
    assert reliability_lower_bound(0, 0.95) == 0.0
    assert math.isclose(reliability_lower_bound(30, 0.95), 0.05 ** (1 / 30), rel_tol=1e-9)
    rl = [reliability_lower_bound(n, 0.95) for n in range(1, 40)]
    assert rl == sorted(rl) and all(0.0 < x < 1.0 for x in rl)

    # survival P(no relapse over m cycles) = R^m, decreasing in m.
    surv = [survival_probability(0.95, m) for m in range(0, 20)]
    assert surv == sorted(surv, reverse=True) and surv[0] == 1.0


def test_cycles_required_is_the_exact_inverse():
    # n = ceil(ln(1−C)/ln(1−p0)); the worked example: 95% confidence of ≤5%/cycle needs 59 cycles.
    assert cycles_required(0.95, 0.05) == 59
    for C, p0 in [(0.95, 0.05), (0.9, 0.1), (0.99, 0.02)]:
        n = cycles_required(C, p0)
        assert confidence_relapse_at_most(n, p0) >= C       # n cycles clear the bar…
        assert confidence_relapse_at_most(n - 1, p0) < C     # …and n−1 do not (tightest)
    # Degenerate inputs are handled, not crashed.
    assert cycles_required(0, 0.05) == 0 and cycles_required(0.95, 0) == 0


def test_assess_is_not_yet_proven_midwindow_and_grades_the_window(session):
    svc, inc, _c1 = to_monitoring(session)
    state_before = inc.state
    svc.advance(inc, 14)  # mid window-1, before the cycle-17 relapse → 14 fault-free cycles

    a = assess(session, inc)
    assert a["available"] is True
    assert a["stable_cycles"] == 14 and a["required_stable_cycles"] == 30

    # Confidence rises with more stable cycles: now (14) < at the full window (30).
    assert a["confidence_now"] < a["confidence_at_window"]
    # With the default target (≤5%/cycle at 95%), 59 cycles are required → not yet proven at 14.
    assert a["cycles_for_target"] == 59
    assert "not yet proven" in a["verdict_confidence"]
    # The 30-cycle contract window grades "adequate" (~78.5% confidence relapse ≤5%/cycle).
    assert a["window_grade"].startswith("adequate")
    # Since 30 < 59, it advises a longer window for the stricter target.
    assert "59" in a["recommendation"]

    # SAFETY: a pure read — it never advances state or touches the verdict.
    assert inc.state == state_before
    assert "Advisory only" in a["advisory"]


def test_assess_reads_an_early_life_infant_mortality_hazard(session):
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 14)
    h = assess(session, inc)["hazard"]
    # F27 recurs ~cycle 17, far inside the 30-cycle window → infant-mortality (Weibull β<1).
    assert 17 in h["relapse_cycles_observed"]
    assert h["pattern"] == "early_life" and h["weibull_shape_hint"] == "β < 1"
    assert h["mean_cycles_to_relapse"] is not None and h["mean_cycles_to_relapse"] < 30
    assert "infant-mortality" in h["interpretation"] or "early-life" in h["interpretation"]


def test_assess_unavailable_before_a_contract_exists(session):
    inc = session.get(Incident, IDS["incident"])  # raw seed: no contract drafted yet
    a = assess(session, inc)
    assert a["available"] is False and "monitoring" in a["reason"]


def test_sprt_bounds_and_decisions():
    # Wald bounds: reject bound > 0 (cross up), accept bound < 0 (cross down).
    a, b = sprt_bounds(0.05, 0.05)
    assert a == math.log(0.95 / 0.05) and b == math.log(0.05 / 0.95)
    assert a > 0 > b

    # A long clean run accepts (recovery demonstrated); a few faults reject; empty stream is undecided.
    assert sprt_evaluate([False] * 30, **_SPRT)["decision"] == "accept"
    assert sprt_evaluate([True] * 3, **_SPRT)["decision"] == "reject"
    assert sprt_evaluate([], **_SPRT)["decision"] == "continue"

    # SAFETY-CRITICAL: with the shipped params the accept threshold falls AFTER the cycle-17 relapse, so
    # 14 clean cycles must NOT yet accept (the test never endorses the hero scenario's false recovery).
    mid = sprt_evaluate([False] * 14, **_SPRT)
    assert mid["decision"] == "continue" and mid["clean_cycles_to_accept"] >= 1
    assert sprt_evaluate([False] * 14, **_SPRT)["decided_at_cycle"] is None


def test_assess_includes_sprt_undecided_midwindow(session):
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 14)
    a = assess(session, inc)
    assert a["sprt"]["decision"] == "continue"            # not yet decided at cycle 14
    assert a["sprt"]["n"] == 14 and a["sprt"]["decided_at_cycle"] is None
    assert "Forecaster" in a["sprt_summary"]               # honest precursor caveat


def test_assess_sprt_accepts_on_a_clean_completed_window(session):
    # Window-2 (after the bearing contingency) runs clean → the sequential test accepts.
    svc, inc, _c2 = to_window2_stable(session, cycles=30)
    a = assess(session, inc)
    assert a["sprt"]["decision"] == "accept"
    assert a["sprt"]["decided_at_cycle"] is not None and a["sprt"]["decided_at_cycle"] <= 20


def test_hazard_is_machine_fault_scoped_not_hardcoded(session):
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 14)
    # F27 has a documented prior → it is applied (relapse history is non-empty, early-life).
    cycles, used_prior = _relapse_history(session, inc)
    assert used_prior is True and 17 in cycles

    # A fault with no documented prior fabricates nothing — the read derives only from live data.
    inc.fault_code = "ZZ99"                                 # not committed; just this test's view
    cycles2, used_prior2 = _relapse_history(session, inc)
    assert used_prior2 is False and cycles2 == []           # no live recurrences on this model yet


def test_assess_reports_proven_once_enough_stable_cycles(session, monkeypatch):
    # Relax the target so the demonstration completes inside a live verification window (window-2, clean).
    monkeypatch.setattr(R, "TARGET_RELAPSE_RATE", 0.15)  # need = ceil(ln0.05/ln0.85) = 19 cycles
    svc, inc, _c2 = to_window2_stable(session, cycles=25)  # 25 fault-free cycles, window still open

    a = assess(session, inc)
    assert a["available"] is True
    assert a["cycles_for_target"] == 19
    assert a["stable_cycles"] >= a["cycles_for_target"]
    assert "statistically demonstrated" in a["verdict_confidence"]
    assert a["confidence_now"] >= a["confidence_level"]
