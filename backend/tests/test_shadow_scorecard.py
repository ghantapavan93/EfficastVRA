"""Tier-0 Shadow Mode Scorecard — runs the deterministic cores over labeled bundles and scores them like a
champion/challenger shadow deployment. The safety-critical assertions: it writes nothing, it catches every
true relapse, and it NEVER verifies a recovery that did not actually hold.
"""

from __future__ import annotations

import pytest

from app.services.shadow_scorecard import run_scorecard


@pytest.fixture(scope="module")
def scorecard():
    return run_scorecard()


@pytest.fixture(scope="module")
def by_key(scorecard):
    return {r["key"]: r for r in scorecard["scenarios"]}


def test_scorecard_writes_nothing(scorecard):
    assert scorecard["summary"]["writes_performed"] == 0


def test_never_verifies_a_failed_recovery(scorecard):
    # The catastrophic error (rubber-stamping a recovery that did not hold) must be zero.
    assert scorecard["false_closure"]["missed_catastrophic"] == 0
    assert scorecard["false_closure"]["recall"] == 1.0   # every true relapse caught


def test_relapses_are_flagged_failed(by_key):
    assert by_key["false_closure_mid"]["proposed"] == "failed"
    assert by_key["false_closure_early"]["proposed"] == "failed"
    assert by_key["false_closure_mid"]["caught"] is True


def test_genuine_recovery_verifies(by_key):
    assert by_key["genuine_recovery"]["proposed"] == "verified"


def test_caution_divergences_abstain_not_false_alarm(scorecard, by_key):
    # On a confounded comparison / untrusted sensor we ABSTAIN (insufficient_evidence) — a safe non-verify,
    # not a 'failed' false alarm. These are the honest "more cautious than the plant" divergences.
    assert by_key["confounded_conditions"]["proposed"] == "insufficient_evidence"
    assert by_key["untrusted_sensor"]["proposed"] == "insufficient_evidence"
    assert scorecard["false_closure"]["fp"] == 0


def test_reconciliation_flags_noise(scorecard):
    totals = scorecard["reconciliation_totals"]
    assert totals.get("duplicate", 0) >= 1     # noisy_stream
    assert totals.get("partial_data", 0) >= 1  # partial_data


def test_scorecard_shape(scorecard):
    s = scorecard["summary"]
    assert s["scenarios"] == 7
    assert s["agreement_rate"] is not None
    assert s["cohens_kappa"] is not None
    assert {"verified", "failed", "insufficient_evidence"} <= set(scorecard["confusion_matrix"]["classes"])
