"""Comparable-Conditions Gate — the causal-honesty backbone. Identical context is COMPARABLE; a key shift
(product/mode/load/sensor/speed) is NOT_COMPARABLE; a minor shift is PARTIALLY; absent context is UNKNOWN.
When a window is NOT_COMPARABLE, the disposition refuses to attribute recovery → INSUFFICIENT_EVIDENCE."""

from __future__ import annotations

from sqlmodel import select

from app.domain.models import Incident, RecoveryWindow
from app.seed.northstar import IDS
from app.services.comparable_conditions import assess_comparability, classify_context
from app.services.disposition import assess_disposition
from app.services.windows import DEFAULT_OPERATING_CONTEXT
from app.workflow.demo import run_scenario
from tests.helpers import to_window2_stable


def test_identical_context_is_comparable():
    base = dict(DEFAULT_OPERATING_CONTEXT)
    assert classify_context(base, dict(base))["classification"] == "COMPARABLE"


def test_key_shift_is_not_comparable():
    base = dict(DEFAULT_OPERATING_CONTEXT)
    obs = {**base, "product": "PKG-XL-20"}  # different product → confound
    r = classify_context(base, obs)
    assert r["classification"] == "NOT_COMPARABLE" and r["key_shifts"] >= 1


def test_minor_shift_is_partial():
    base = dict(DEFAULT_OPERATING_CONTEXT)
    obs = {**base, "ambient_c": base["ambient_c"] + 12}  # ambient drift beyond tol (minor weight)
    assert classify_context(base, obs)["classification"] == "PARTIALLY_COMPARABLE"


def test_absent_context_is_unknown():
    assert classify_context({}, {})["classification"] == "UNKNOWN"


def test_hero_window_is_comparable(session):
    run_scenario(session, log=lambda *a: None)
    inc = session.get(Incident, IDS["incident"])
    assert assess_comparability(session, inc)["classification"] == "COMPARABLE"


def test_not_comparable_drives_insufficient_in_disposition(session):
    _svc, inc, c2 = to_window2_stable(session, cycles=30)
    win = session.exec(
        select(RecoveryWindow).where(RecoveryWindow.contract_id == c2.id)
        .order_by(RecoveryWindow.sequence.desc())
    ).first()
    # the verification window ran at half speed under a heavier load → not comparable to normal
    win.observed_context = {**win.observed_context, "speed_pct": 47.5, "load": "high"}
    session.add(win)
    session.commit()

    assert assess_comparability(session, inc)["classification"] == "NOT_COMPARABLE"
    d = assess_disposition(session, inc)
    assert d["comparability"]["classification"] == "NOT_COMPARABLE"
    assert d["disposition"] == "INSUFFICIENT_EVIDENCE"
    assert any("comparable" in r.lower() for r in d["reasons"])
