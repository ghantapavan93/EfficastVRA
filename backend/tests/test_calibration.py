"""Phase 36c — the calibration harness makes the Expected Recovery Signature falsifiable.

It must be (a) deterministic/reproducible and (b) demonstrate the signature has *real* skill at telling a
genuine recovery from a latent relapse (not a tautology). See docs/CAUSAL_RECOVERY_RESEARCH.md §6.
"""

from __future__ import annotations

from app.services.calibration import run_calibration


def test_calibration_is_reproducible():
    a = run_calibration(trials=300, seed=3)
    b = run_calibration(trials=300, seed=3)
    assert a["brier"] == b["brier"]
    assert a["auc"] == b["auc"]
    assert a["reliability_curve"] == b["reliability_curve"]


def test_signature_has_real_skill_and_is_calibrated():
    r = run_calibration(trials=400, seed=7)
    assert r["n_genuine"] + r["n_false"] == 400
    assert 0.0 <= r["brier"] <= 1.0
    assert r["brier"] < 0.25            # beats no-skill (Brier ≈ 0.25 at a 50/50 base rate)
    assert r["auc"] > 0.70             # genuinely separates genuine recovery from latent relapse
    assert r["reliability_curve"]      # non-empty bins
    assert all(
        0.0 <= pt["p_pred"] <= 1.0 and 0.0 <= pt["observed"] <= 1.0 and pt["count"] > 0
        for pt in r["reliability_curve"]
    )
    assert r["early_warning_rate"] > 0.5   # most latent relapses are flagged before closure


def test_brier_decomposition_is_consistent():
    r = run_calibration(trials=300, seed=11)
    # Murphy decomposition: brier ≈ reliability − resolution + uncertainty (binning makes it approximate)
    approx = r["brier_reliability"] - r["brier_resolution"] + r["brier_uncertainty"]
    assert abs(approx - r["brier"]) < 0.05
