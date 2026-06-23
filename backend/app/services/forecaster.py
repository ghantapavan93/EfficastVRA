"""Recovery Forecaster — predict whether a repair will actually hold, *before* the fault recurs.

A genuinely new primitive. Conventional predictive maintenance forecasts equipment *failure* from raw
sensors. This forecasts **recovery**: given the two competing hypotheses the agent raised at triage —
H1 "the intervention fixed it" vs H2 "a latent fault will relapse" — it scores which one the live
post-intervention trajectory supports each cycle, and flags a likely false recovery several cycles
*before* the originating fault actually fires.

It reads a degradation **precursor** the headline metrics mask (e.g. drive-end bearing high-frequency
vibration / crest factor): vibration, temperature, cycle time and scrap can all look recovered while
the precursor quietly rises. That divergence is the early tell.

IMPORTANT — this is **advisory**. It never decides closure, never reopens an incident, never acts. The
deterministic evaluator still requires a real condition violation to reopen, and a human still decides.
The value is *earlier insight*, not automated action on a prediction (so a wrong forecast can't cause a
false close or a false reopen).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlmodel import Session, select

from app.domain.models import RecoveryContract, RecoveryObservation
from app.services.windows import get_active_window

WARN_THRESHOLD = 0.6   # P(relapse) at/above which we raise an early "false recovery" warning


@dataclass
class Forecast:
    available: bool
    observed_cycles: int = 0
    p_recovery_holds: float = 0.5
    p_relapse: float = 0.5
    predicted_relapse_cycle: Optional[int] = None
    fault_cycle: Optional[int] = None
    lead_cycles: Optional[int] = None       # warning given this many cycles before the fault fired
    divergence: float = 0.0                  # latest precursor level (0..1)
    leading_indicator: str = ""
    hypotheses: list = field(default_factory=list)
    series: list = field(default_factory=list)  # [{cycle, p_relapse}] for the UI
    headline: str = ""


def _p_relapse(precursor: float, slope: float) -> float:
    return round(min(0.98, max(0.02, 0.7 * precursor + 0.3 * min(1.0, slope * 10.0))), 2)


def forecast(session: Session, contract: RecoveryContract) -> Forecast:
    window = get_active_window(session, contract)
    if window is None:
        return Forecast(available=False)
    obs = session.exec(
        select(RecoveryObservation).where(RecoveryObservation.window_id == window.id)
        .order_by(RecoveryObservation.cycle_index)  # type: ignore[arg-type]
    ).all()
    pts = [(o.cycle_index, o.bearing_precursor) for o in obs if o.bearing_precursor is not None]
    if not pts:
        return Forecast(available=False, observed_cycles=len(obs))

    base_cycle, base_precursor = pts[0]
    predicted: Optional[int] = None
    series: list = []
    for ci, pc in pts:
        slope = (pc - base_precursor) / max(1, ci - base_cycle)
        p = _p_relapse(pc, slope)
        series.append({"cycle": ci, "p_relapse": p})
        if predicted is None and p >= WARN_THRESHOLD:
            predicted = ci

    latest_precursor = pts[-1][1]
    p_relapse = series[-1]["p_relapse"]
    fault_cycle = next((o.cycle_index for o in obs if o.fault_code), None)
    lead = (fault_cycle - predicted) if (fault_cycle and predicted and predicted < fault_cycle) else None

    if fault_cycle and predicted and lead:
        headline = (f"Forecast called it: false-recovery warning at cycle {predicted}; fault confirmed "
                    f"at cycle {fault_cycle} — {lead} cycles of lead time.")
    elif predicted:
        headline = (f"Early warning: trajectory is diverging toward a relapse (flagged at cycle "
                    f"{predicted}). Recovery is not yet proven — keep monitoring.")
    else:
        headline = "On track: the trajectory supports a holding recovery (no relapse precursor)."

    hypotheses = [
        {"id": "H1", "label": "Intervention corrected the fault — recovery holds",
         "support": round(1.0 - p_relapse, 2)},
        {"id": "H2", "label": "Latent drive-end bearing degradation — will relapse",
         "support": p_relapse,
         "evidence": "bearing vibration precursor rising while headline metrics look recovered"},
    ]
    return Forecast(
        available=True, observed_cycles=len(obs), p_recovery_holds=round(1.0 - p_relapse, 2),
        p_relapse=p_relapse, predicted_relapse_cycle=predicted, fault_cycle=fault_cycle, lead_cycles=lead,
        divergence=round(latest_precursor, 3),
        leading_indicator="drive-end bearing vibration precursor" if latest_precursor > 0.3 else "",
        hypotheses=hypotheses, series=series, headline=headline,
    )
