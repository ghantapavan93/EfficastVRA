"""Sensor Trust Gate — a measurement you can't trust can't satisfy a hard recovery condition.

Classifies a sensor's recent samples as TRUSTED / DEGRADED / UNTRUSTED / UNKNOWN from deterministic checks:
missing samples, impossible (out-of-physical-range) values, flatline (stuck), excessive noise, calibration
overdue, sensor replacement, mapping change, and clock discontinuity. Same philosophy as the
comparable-conditions ceiling (rule ccr-1.0): an **UNTRUSTED or UNKNOWN** sensor forces the recovery to
INSUFFICIENT_EVIDENCE rather than satisfying a hard condition. Read-only & advisory; the deterministic
evaluator still owns the verdict.

(Drift detection is deliberately omitted from the default checks: a recovering channel — vibration settling,
temperature declining — is *expected* to move, so a naive drift test would false-positive. Drift is only
meaningful for channels asserted stationary; that refinement is noted for a later pass.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, pstdev
from typing import Optional

from sqlmodel import Session, select

from app.domain.base import utcnow
from app.domain.models import Incident, RecoveryContract, RecoveryObservation, RecoveryWindow

# physical plausibility per metric (PROTOTYPE_ASSUMPTION)
PLAUSIBLE: dict[str, tuple[float, float]] = {
    "vibration": (0.0, 50.0), "temperature": (-20.0, 250.0), "cycle_time": (0.1, 600.0),
    "scrap_pct": (0.0, 100.0), "bearing_precursor": (0.0, 10.0),
}
_TRUST_ORDER = {"UNTRUSTED": 0, "UNKNOWN": 1, "DEGRADED": 2, "TRUSTED": 3}
_LIVE_METRICS = ("vibration", "temperature", "cycle_time")


@dataclass
class SensorTrustResult:
    status: str                    # TRUSTED | DEGRADED | UNTRUSTED | UNKNOWN
    metric: str = ""
    checks: list[dict] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def classify_sensor(
    samples: list,
    *,
    metric: str = "",
    plausible: Optional[tuple[float, float]] = None,
    calibration_due: Optional[datetime] = None,
    as_of: Optional[datetime] = None,
    replaced: bool = False,
    mapping_changed: bool = False,
    min_samples: int = 8,
    noise_cv_max: float = 0.6,
) -> SensorTrustResult:
    as_of = as_of or utcnow()
    vals = [float(v) for v in samples if v is not None]
    checks: list[dict] = []
    reasons: list[str] = []

    def chk(name: str, ok: bool, detail: str = "") -> bool:
        checks.append({"name": name, "ok": ok, "detail": detail})
        return ok

    if len(vals) < min_samples:
        return SensorTrustResult("UNKNOWN", metric,
                                 [{"name": "samples", "ok": False, "detail": f"{len(vals)} < {min_samples}"}],
                                 ["insufficient samples to assess the sensor"])

    lo, hi = plausible or PLAUSIBLE.get(metric, (-1e12, 1e12))
    impossible = [v for v in vals if v < lo or v > hi]
    chk("plausible_range", not impossible, f"{len(impossible)} outside [{lo}, {hi}]")
    flat = (max(vals) - min(vals)) == 0.0
    chk("not_flatline", not flat, "zero variance (stuck)" if flat else "")
    m = mean(vals)
    sd = pstdev(vals)
    cv = (sd / abs(m)) if m else (0.0 if sd == 0 else 1e9)
    noisy = cv > noise_cv_max
    chk("noise", not noisy, f"cv={cv:.2f}")
    cal_overdue = calibration_due is not None and as_of > calibration_due
    chk("calibration", not cal_overdue, "overdue" if cal_overdue else "")
    chk("not_replaced_midwindow", not replaced, "replaced" if replaced else "")
    chk("no_mapping_change", not mapping_changed, "mapping changed" if mapping_changed else "")

    if impossible or flat:
        reasons.append("impossible values out of physical range" if impossible else "flatlined / stuck sensor")
        return SensorTrustResult("UNTRUSTED", metric, checks, reasons)
    if cal_overdue or replaced or mapping_changed or noisy:
        if cal_overdue:
            reasons.append("calibration overdue")
        if replaced:
            reasons.append("sensor replaced mid-window")
        if mapping_changed:
            reasons.append("mapping changed mid-window")
        if noisy:
            reasons.append("excessive noise")
        return SensorTrustResult("DEGRADED", metric, checks, reasons)
    return SensorTrustResult("TRUSTED", metric, checks, ["all checks passed"])


def _series(observations: list[RecoveryObservation], field_: str) -> list:
    return [getattr(o, field_) for o in observations]


def assess_sensor_trust(session: Session, incident: Incident, *, as_of: Optional[datetime] = None) -> dict:
    """Live read: classify the machine sensors over the active verification window's observations and return
    the worst status (the gate is only as strong as its weakest trusted sensor). Read-only."""
    contract = (session.get(RecoveryContract, incident.current_contract_id)
                if incident.current_contract_id else None)
    if contract is None:
        return {"available": False, "incident_id": incident.id,
                "reason": "No recovery contract yet — sensor trust is available once monitoring begins."}
    win = session.exec(
        select(RecoveryWindow).where(RecoveryWindow.contract_id == contract.id)
        .order_by(RecoveryWindow.sequence.desc())  # type: ignore[attr-defined]
    ).first()
    obs = session.exec(
        select(RecoveryObservation).where(RecoveryObservation.window_id == win.id)
        .order_by(RecoveryObservation.cycle_index)  # type: ignore[attr-defined]
    ).all() if win else []

    per_metric = [classify_sensor(_series(obs, m), metric=m, as_of=as_of) for m in _LIVE_METRICS]
    worst = min(per_metric, key=lambda r: _TRUST_ORDER.get(r.status, 1))
    return {
        "available": True,
        "incident_id": incident.id,
        "status": worst.status,
        "satisfies_hard_conditions": worst.status == "TRUSTED",   # only a TRUSTED sensor may
        "reasons": worst.reasons,
        "per_metric": [{"metric": r.metric, "status": r.status, "reasons": r.reasons, "checks": r.checks}
                       for r in per_metric],
        "basis": ("Advisory & read-only. A measurement we can't trust can't satisfy a hard recovery "
                  "condition — an UNTRUSTED or UNKNOWN sensor caps the recovery at INSUFFICIENT_EVIDENCE "
                  "(same family as the comparable-conditions ceiling). Synthetic PROTOTYPE_ASSUMPTION."),
    }
