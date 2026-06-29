"""OEE-Restoration Verification — did the recovery actually restore OEE, or just close the order?

Efficast's core metric is **OEE = Availability × Performance × Quality** (live from the PLC). This module
applies the Verified-Recovery thesis to that exact metric: a closed work order is not proof that OEE came
back. From the verification-window cycle observations it recomputes A·P·Q against the machine's baseline and
reports whether OEE was *restored* — and, crucially, *which factor* still lags (e.g. quality recovered but
performance is still depressed).

ADVISORY / READ-ONLY. This is a verification lens, not a gate: the deterministic evaluator + the
comparable-conditions ceiling still own closure. OEE figures derive from synthetic cycle data and the
baseline/target constants below are PROTOTYPE_ASSUMPTIONs (env-configurable) — not real plant measurements.
"""

from __future__ import annotations

import os

from sqlmodel import Session, select

from app.domain.models import Incident, Machine, RecoveryObservation

# ── PROTOTYPE_ASSUMPTION constants (env-tunable; not real plant data) ──────────────────────────────
# Baseline planned availability — a clean reference run has no modelled stoppages, so we assume a
# realistic-but-illustrative planned availability rather than a perfect 1.0.
BASELINE_AVAILABILITY = float(os.getenv("VRA_OEE_BASELINE_AVAILABILITY", "0.96"))
# The classic "world-class OEE" benchmark, shown for context only.
WORLD_CLASS_OEE = float(os.getenv("VRA_OEE_WORLD_CLASS", "0.85"))
# How close recovered OEE must come to baseline to count as "restored".
RESTORATION_TOLERANCE = float(os.getenv("VRA_OEE_RESTORATION_TOLERANCE", "0.03"))
# Trailing window (in cycles) for the smoothed OEE trajectory.
_TRAJECTORY_WINDOW = 5


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _factors(obs: list[RecoveryObservation], *, ideal_cycle_s: float, baseline_scrap_pct: float) -> dict:
    """Availability · Performance · Quality over a set of cycle observations.

    A = share of cycles that ran fault-free · P = ideal/actual cycle time (capped) · Q = good-piece rate.
    """
    n = len(obs)
    if n == 0:
        return {"availability": None, "performance": None, "quality": None, "oee": None, "cycles": 0}
    faulted = sum(1 for o in obs if o.fault_code)
    availability = _clamp01(1.0 - faulted / n)
    perfs = [
        _clamp01(ideal_cycle_s / o.cycle_time) for o in obs
        if o.cycle_time and o.cycle_time > 0 and ideal_cycle_s > 0
    ]
    performance = _clamp01(sum(perfs) / len(perfs)) if perfs else 1.0
    quals = [_clamp01(1.0 - (o.scrap_pct or 0.0) / 100.0) for o in obs]
    quality = _clamp01(sum(quals) / len(quals)) if quals else _clamp01(1.0 - baseline_scrap_pct / 100.0)
    return {
        "availability": round(availability, 4),
        "performance": round(performance, 4),
        "quality": round(quality, 4),
        "oee": round(availability * performance * quality, 4),
        "cycles": n,
    }


def _pct(x) -> float | None:
    return None if x is None else round(x * 100.0, 1)


def assess_oee_restoration(session: Session, incident: Incident) -> dict:
    """Advisory: recompute OEE over the verification window and compare it to the machine baseline.
    Never changes state or closure — a verification lens on Efficast's own headline metric."""
    machine = session.get(Machine, incident.machine_id)
    baseline = (machine.baseline if machine else None) or {}
    ideal_cycle = float(baseline.get("cycle_time_s") or 0.0)
    baseline_scrap = float(baseline.get("scrap_pct") or 0.0)

    obs = session.exec(
        select(RecoveryObservation)
        .where(RecoveryObservation.incident_id == incident.id)
        .order_by(RecoveryObservation.cycle_index)  # type: ignore[arg-type]
    ).all()

    if not machine or ideal_cycle <= 0 or not obs:
        return {"available": False,
                "reason": "OEE restoration needs a machine baseline and verification-window cycles."}

    # Baseline reference OEE (clean run): performance is nominal, quality from baseline scrap.
    baseline_q = _clamp01(1.0 - baseline_scrap / 100.0)
    baseline_oee = {
        "availability": round(BASELINE_AVAILABILITY, 4),
        "performance": 1.0,
        "quality": round(baseline_q, 4),
        "oee": round(BASELINE_AVAILABILITY * 1.0 * baseline_q, 4),
    }

    # "Recovered" = the most recent stable run (last window's tail); fall back to all observations.
    recovered_obs = [o for o in obs if not o.fault_code][-incident_required_tail(session, incident):] or obs
    recovered = _factors(recovered_obs, ideal_cycle_s=ideal_cycle, baseline_scrap_pct=baseline_scrap)

    # Smoothed OEE trajectory across the whole monitoring history (shows the dip + the recovery).
    trajectory: list[dict] = []
    for i in range(len(obs)):
        window = obs[max(0, i - _TRAJECTORY_WINDOW + 1): i + 1]
        f = _factors(window, ideal_cycle_s=ideal_cycle, baseline_scrap_pct=baseline_scrap)
        trajectory.append({"cycle": obs[i].cycle_index, "oee": f["oee"]})

    restored = bool(
        recovered["oee"] is not None
        and recovered["oee"] >= baseline_oee["oee"] * (1.0 - RESTORATION_TOLERANCE)
    )
    # Which factor still lags baseline (the honest "closed but not fully restored" signal)?
    lagging = _lagging_factor(recovered, baseline_oee)

    delta = None if recovered["oee"] is None else round(recovered["oee"] - baseline_oee["oee"], 4)
    return {
        "available": True,
        "restored": restored,
        "baseline_oee": {**baseline_oee, "oee_pct": _pct(baseline_oee["oee"])},
        "recovered_oee": {**recovered, "oee_pct": _pct(recovered["oee"])},
        "delta": delta,
        "delta_pct": _pct(delta),
        "lagging_factor": lagging,
        "factors": [
            {"key": "availability", "label": "Availability",
             "baseline": _pct(baseline_oee["availability"]), "recovered": _pct(recovered["availability"]),
             "restored": _factor_restored(recovered["availability"], baseline_oee["availability"])},
            {"key": "performance", "label": "Performance",
             "baseline": _pct(baseline_oee["performance"]), "recovered": _pct(recovered["performance"]),
             "restored": _factor_restored(recovered["performance"], baseline_oee["performance"])},
            {"key": "quality", "label": "Quality",
             "baseline": _pct(baseline_oee["quality"]), "recovered": _pct(recovered["quality"]),
             "restored": _factor_restored(recovered["quality"], baseline_oee["quality"])},
        ],
        "trajectory": trajectory,
        "world_class_oee_pct": _pct(WORLD_CLASS_OEE),
        "headline": _headline(restored, lagging, delta),
        "basis": (
            "OEE = Availability × Performance × Quality, recomputed from verification-window cycles vs the "
            "machine baseline. Advisory only — closure is owned by the deterministic evaluator, not OEE. "
            "Baseline availability/world-class target are PROTOTYPE_ASSUMPTIONs over synthetic data."
        ),
    }


def _factor_restored(recovered, baseline) -> bool:
    return recovered is not None and baseline is not None and recovered >= baseline * (1.0 - RESTORATION_TOLERANCE)


def _lagging_factor(recovered: dict, baseline: dict) -> str | None:
    """The single OEE factor furthest below its baseline (if any meaningfully lags)."""
    gaps = {
        k: (baseline[k] - recovered[k])
        for k in ("availability", "performance", "quality")
        if recovered.get(k) is not None and baseline.get(k) is not None
    }
    worst = max(gaps, key=gaps.get) if gaps else None
    if worst is None or gaps[worst] <= RESTORATION_TOLERANCE:
        return None
    return worst


def _headline(restored: bool, lagging: str | None, delta) -> str:
    if restored:
        return "OEE restored to baseline — recovery confirmed on the headline metric."
    if lagging:
        return f"Order closed, but OEE is not fully restored — {lagging} still lags baseline."
    return "Order closed, but OEE has not returned to baseline."


def incident_required_tail(session: Session, incident: Incident) -> int:
    """The number of trailing stable cycles to treat as the 'recovered' run — the contract's required
    stable window when known, else a sensible default."""
    from app.domain.models import RecoveryWindow

    win = session.exec(
        select(RecoveryWindow)
        .where(RecoveryWindow.incident_id == incident.id)
        .order_by(RecoveryWindow.sequence.desc())  # type: ignore[attr-defined]
    ).first()
    return int(win.required_stable_cycles) if win and win.required_stable_cycles else 30
