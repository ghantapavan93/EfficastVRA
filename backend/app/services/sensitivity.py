"""Counterfactual contract calibration — "was the verification window the right length?"

The Recovery Contract requires N stable cycles before it will declare recovery. But *why N?* This replays
the **deterministic verifier over the real observation trajectory** at a sweep of candidate window
lengths and reports, for each, what the verdict *would* have been:

  • A window short enough to be reached before the originating fault recurs → the contract would have
    declared a **FALSE recovery** at that cycle (the exact failure mode the product exists to prevent).
  • A window at least as long as the relapse cycle → the recurrence violates the NOT_RECUR condition
    first, so the contract correctly **catches it** (reopens) instead of closing.

So the **minimum safe window** equals the relapse cycle: any shorter window would have been fooled. This
is the deterministic complement to the statistical reliability layer — together they bracket calibration:
*relapse-cycle (to catch THIS fault) ≤ contract window ≤ cycles-for-target (for statistical confidence).*

Deterministic, read-only, **advisory** — it grades the contract's window using the recorded trajectory;
it never changes the verdict. It replays the same ``is_stable_observation`` logic the live engine uses.

References: see docs/RELIABILITY_STATISTICS.md (the calibration story).
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.domain.models import (
    Incident,
    RecoveryCondition,
    RecoveryContract,
    RecoveryObservation,
    RecoveryWindow,
)
from app.services.evaluator import is_stable_observation

# Candidate window lengths to stress-test (plus the actual window and the relapse cycle, added at runtime).
_SWEEP = [5, 10, 15, 20, 25, 30, 40, 50]


def _ordered_obs(session: Session, window_id: str) -> list[RecoveryObservation]:
    return session.exec(
        select(RecoveryObservation).where(RecoveryObservation.window_id == window_id)
        .order_by(RecoveryObservation.cycle_index)  # type: ignore[arg-type]
    ).all()


def analyze(session: Session, incident: Incident) -> dict:
    """Counterfactual calibration of the verification window for an incident (advisory)."""
    windows = session.exec(
        select(RecoveryWindow).where(RecoveryWindow.incident_id == incident.id)
        .order_by(RecoveryWindow.sequence)  # type: ignore[arg-type]
    ).all()
    if not windows:
        return {"available": False, "incident_id": incident.id,
                "reason": "No verification window yet — calibration replay needs an observed trajectory."}

    # Prefer the window that actually contains a relapse — that's the one worth stress-testing.
    chosen, obs = None, []
    for w in windows:
        o = _ordered_obs(session, w.id)
        if any(x.fault_code for x in o):
            chosen, obs = w, o
            break
    if chosen is None:
        chosen = windows[-1]
        obs = _ordered_obs(session, chosen.id)
    if not obs:
        return {"available": False, "incident_id": incident.id,
                "reason": "The verification window has no observations yet."}

    contract = session.get(RecoveryContract, chosen.contract_id)
    conditions = session.exec(
        select(RecoveryCondition).where(RecoveryCondition.contract_id == chosen.contract_id)
    ).all()

    # Replay the stable-streak progression exactly as the live cycle engine does.
    relapse_cycle = next((o.cycle_index for o in obs if o.fault_code), None)
    streak = 0
    reach: dict[int, int] = {}  # required_stable_cycles k -> first cycle the streak reaches k
    for o in obs:
        if is_stable_observation(o, conditions):
            streak += 1
            reach.setdefault(streak, o.cycle_index)
        else:
            streak = 0
    max_stable_streak = max(reach) if reach else 0
    actual_required = chosen.required_stable_cycles

    ks = sorted({*_SWEEP, actual_required, *( [relapse_cycle] if relapse_cycle else [] )})
    sweep = []
    for k in ks:
        close_cycle = reach.get(k)
        if close_cycle is not None and (relapse_cycle is None or close_cycle < relapse_cycle):
            outcome = "false_close" if relapse_cycle else "verified"
        else:
            outcome = "caught_relapse" if relapse_cycle else "incomplete"
            close_cycle = None
        sweep.append({"required_stable_cycles": k, "outcome": outcome, "close_cycle": close_cycle,
                      "is_contract": k == actual_required})

    min_safe_window = relapse_cycle  # any window ≥ the relapse cycle catches it; anything shorter is fooled
    margin = (actual_required - relapse_cycle) if relapse_cycle else None
    safe = relapse_cycle is None or actual_required >= relapse_cycle

    if relapse_cycle:
        headline = (f"Min safe window {min_safe_window} · contract {actual_required} · "
                    f"margin {margin:+d} cycles")
        verdict = (
            f"The {actual_required}-cycle window is {'safely calibrated' if safe else 'TOO SHORT'}: it "
            f"{'extends' if margin and margin >= 0 else 'falls'} {abs(margin)} cycle(s) "
            f"{'past' if margin and margin >= 0 else 'short of'} the cycle-{relapse_cycle} relapse. Any "
            f"window ≤ {relapse_cycle - 1} cycles would have declared a FALSE recovery before the fault "
            f"reappeared — exactly what the contract exists to prevent."
        )
    else:
        headline = f"No relapse in this window (max stable streak {max_stable_streak})"
        verdict = ("No fault recurred in the replayed trajectory, so the window cannot be stress-tested "
                   "against a relapse here — calibration is unconstrained by this run.")

    return {
        "available": True,
        "incident_id": incident.id,
        "window_sequence": chosen.sequence,
        "relapse_cycle": relapse_cycle,
        "max_stable_streak": max_stable_streak,
        "actual_required_stable_cycles": actual_required,
        "min_safe_window": min_safe_window,
        "margin_cycles": margin,
        "safe": bool(safe),
        "sweep": sweep,
        "headline": headline,
        "verdict": verdict,
        "advisory": ("Advisory only — a deterministic replay of the recorded trajectory at alternative "
                     "window lengths. It grades the contract's calibration; it never changes the verdict."),
    }
