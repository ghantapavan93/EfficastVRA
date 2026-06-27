"""Calibration harness for the Expected Recovery Signature — makes the advisory layer *falsifiable*.

A deterministic Monte-Carlo: generate K labelled synthetic scenarios (a genuine recovery vs a latent
relapse), score each with the SAME signature core the live path uses (`recovery_signature.score_observations`),
and measure how well the signature's alignment predicts the truth:

- **Brier score** (+ the Murphy reliability/resolution/uncertainty decomposition) — lower is better.
- a **reliability diagram** (binned predicted-probability vs observed frequency) — should track the diagonal.
- **ROC AUC** — threshold-free discrimination (0.5 = chance, 1.0 = perfect).
- **early-warning rate** — fraction of latent relapses the signature flags before closure.

Headline metrics are kept in-spec for *both* classes, so the signature must earn its discrimination from
the genuinely informative signals (fault non-recurrence + the degradation precursor) — exactly the
correlation-vs-causation distinction the layer exists to make. Read-only, advisory, fully reproducible
(seeded RNG, no wall-clock). Synthetic PROTOTYPE_ASSUMPTION — never real plant data.

This is the audit's "single biggest lever" (ARCHITECTURE_AUDIT Theme C1) and the falsifiability gate in
the GO‑conditional verdict (CAUSAL_RECOVERY_RESEARCH §6).
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from app.domain.enums import CompareOp, ConditionKind
from app.domain.models import RecoveryCondition, RecoveryObservation
from app.services.recovery_signature import score_observations

_DT = datetime(2026, 1, 1)        # fixed (scoring is time-agnostic; keeps the harness wall-clock-free)
_REQUIRED_STABLE = 30
_WINDOW = 20                      # cycles observed before the (possibly latent) relapse


def _conveyor_conditions() -> list[RecoveryCondition]:
    """An in-memory conveyor contract's conditions (not persisted) — the signature is derived from these."""
    def c(**kw) -> RecoveryCondition:
        return RecoveryCondition(tenant_id="calib", contract_id="calib", incident_id="calib", **kw)

    return [
        c(key="vibration_rms", kind=ConditionKind.MACHINE, op=CompareOp.LTE, threshold=4.0, baseline=3.1),
        c(key="temperature_trend", kind=ConditionKind.MACHINE, op=CompareOp.DECLINING, baseline=63.0),
        c(key="fault_f27", kind=ConditionKind.MACHINE, op=CompareOp.NOT_RECUR, fault_code="F27"),
        c(key="cycle_time", kind=ConditionKind.MACHINE, op=CompareOp.WITHIN_PCT, threshold=0.05, baseline=12.2),
        c(key="scrap", kind=ConditionKind.PRODUCTION, op=CompareOp.LT, threshold=2.0, baseline=1.6),
        c(key="stable_cycles", kind=ConditionKind.PRODUCTION, op=CompareOp.COUNT_GTE, threshold=30),
        c(key="first_piece", kind=ConditionKind.QUALITY, op=CompareOp.EQ, threshold=1.0),
    ]


def _scenario(rng: np.random.Generator) -> tuple[list[RecoveryObservation], bool]:
    """One labelled scenario. Genuine: precursor flat (sometimes a transient false-alarm spike). Latent
    relapse: precursor rises (slow→hard, fast→easy), with an in-window fault some of the time. Headline
    metrics stay in-spec for both classes, so only the discriminating signals separate them."""
    genuine = bool(rng.random() < 0.5)
    false_alarm = genuine and rng.random() < 0.25
    slow = (not genuine) and rng.random() < 0.5
    # Slow latent degrades barely clear the tolerance → genuinely ambiguous (the signature *should*
    # struggle on these); fast degrades are clear. Genuine lines carry a touch of upward sensor drift,
    # so the classes overlap and the reliability curve is honest rather than a perfect step.
    if genuine:
        slope = rng.uniform(-0.002, 0.006)
    else:
        slope = rng.uniform(0.004, 0.02) if slow else rng.uniform(0.08, 0.16)
    fault_cycle = (int(rng.integers(_WINDOW // 2, _WINDOW))
                   if (not genuine and rng.random() < 0.4) else None)

    obs: list[RecoveryObservation] = []
    for i in range(_WINDOW):
        vib = 3.1 + rng.normal(0, 0.12)
        temp = 70.0 - 0.35 * i + rng.normal(0, 0.3)            # declining, in-spec
        cyc = 12.2 + rng.normal(0, 0.08)
        scrap = 1.5 + rng.normal(0, 0.15)
        prec = 0.10 + slope * i + rng.normal(0, 0.01)
        if false_alarm:
            prec += 0.5 * float(np.exp(-((i - _WINDOW / 2) ** 2) / 4.0))   # transient spike, then returns
        fault = "F27" if (fault_cycle is not None and i >= fault_cycle) else None
        obs.append(RecoveryObservation(
            tenant_id="calib", incident_id="calib", contract_id="calib", window_id="calib",
            cycle_index=i + 1, at=_DT,
            vibration=round(float(vib), 3), temperature=round(float(temp), 2),
            cycle_time=round(float(cyc), 3), scrap_pct=round(max(0.0, float(scrap)), 3),
            fault_code=fault, bearing_precursor=round(max(0.0, float(prec)), 4),
        ))
    return obs, genuine


def _auc(preds: np.ndarray, ys: np.ndarray) -> float:
    """ROC AUC = P(score(genuine) > score(false)), tie-aware. Deterministic."""
    pos, neg = preds[ys == 1], preds[ys == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    wins = sum(float(np.sum(p > neg) + 0.5 * np.sum(p == neg)) for p in pos)
    return wins / (len(pos) * len(neg))


def run_calibration(*, trials: int = 400, seed: int = 7, bins: int = 10) -> dict:
    """Run the harness and return calibration metrics. Deterministic given (trials, seed, bins)."""
    rng = np.random.default_rng(seed)
    conds = _conveyor_conditions()
    preds: list[float] = []
    ys: list[float] = []
    for _ in range(trials):
        obs, genuine = _scenario(rng)
        res = score_observations(conds, obs, required_stable=_REQUIRED_STABLE)
        preds.append((res.alignment + 1.0) / 2.0)          # alignment [-1,1] → predicted P(holds) [0,1]
        ys.append(1.0 if genuine else 0.0)
    p = np.array(preds)
    y = np.array(ys)

    brier = float(np.mean((p - y) ** 2))
    ybar = float(np.mean(y))
    edges = np.linspace(0.0, 1.0, bins + 1)
    curve: list[dict] = []
    rel = resol = 0.0
    for b in range(bins):
        lo, hi = edges[b], edges[b + 1]
        mask = (p >= lo) & (p <= hi) if b == bins - 1 else (p >= lo) & (p < hi)
        k = int(mask.sum())
        if k == 0:
            continue
        p_pred, observed = float(p[mask].mean()), float(y[mask].mean())
        curve.append({"p_pred": round(p_pred, 3), "observed": round(observed, 3), "count": k})
        rel += k * (p_pred - observed) ** 2
        resol += k * (observed - ybar) ** 2

    n_false = int((y == 0).sum())
    return {
        "available": True,
        "trials": trials,
        "seed": seed,
        "brier": round(brier, 4),
        "brier_reliability": round(rel / trials, 4),     # lower = better calibrated
        "brier_resolution": round(resol / trials, 4),    # higher = more discriminating
        "brier_uncertainty": round(ybar * (1 - ybar), 4),
        "auc": round(_auc(p, y), 4),
        "accuracy": round(float(np.mean((p >= 0.5) == (y >= 0.5))), 4),
        "early_warning_rate": round(float(np.mean(p[y == 0] < 0.5)) if n_false else 0.0, 4),
        "n_genuine": int((y == 1).sum()),
        "n_false": n_false,
        "reliability_curve": curve,
        "is_synthetic": True,
        "basis": ("Deterministic Monte-Carlo over seeded synthetic scenarios (genuine recovery vs latent "
                  "relapse). Brier (lower=better) measures calibration+accuracy; AUC is threshold-free "
                  "discrimination; the reliability curve should track the diagonal. Synthetic "
                  "PROTOTYPE_ASSUMPTION — not real plant data; it measures the signature's internal skill, "
                  "not real-world recovery."),
    }
