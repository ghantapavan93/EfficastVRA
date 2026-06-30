"""Recovery Twin — the recovery trajectory, cycle by cycle, scrubbable.

A static verdict hides the *story*: vibration settling, the stable-cycle streak building, then (sometimes) a
fault returning and resetting everything. The Twin replays the recorded observations across every verification
window so the UI can scrub through them — "apparent recovery here, relapse there, verified there".

Pure projection over RecoveryObservation + the contract's conditions. It recomputes the stable streak exactly
as the evaluator did (so the scrub matches the verdict); it decides nothing and changes no state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.domain.models import (
    Incident,
    RecoveryCondition,
    RecoveryObservation,
    RecoveryWindow,
)
from app.services.evaluator import is_stable_observation


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def build_twin(session: Session, incident: Incident) -> dict:
    # Windows belong to the *incident*, not one contract — a reopen spins up a V2 contract with its own
    # window, while the original observations live on the V1 window. Aggregate across all of them.
    windows = session.exec(
        select(RecoveryWindow).where(RecoveryWindow.incident_id == incident.id)
        .order_by(RecoveryWindow.sequence)  # type: ignore[arg-type]
    ).all()
    if not windows:
        return {"available": False,
                "reason": "No recovery trajectory yet — it begins once a contract is monitoring."}

    # Conditions can differ per contract (V1 vs the contingency V2); cache per contract for the streak calc.
    _cond_cache: dict[str, list[RecoveryCondition]] = {}

    def conditions_for(contract_id: str) -> list[RecoveryCondition]:
        if contract_id not in _cond_cache:
            _cond_cache[contract_id] = session.exec(
                select(RecoveryCondition).where(RecoveryCondition.contract_id == contract_id)
            ).all()
        return _cond_cache[contract_id]

    # Reference lines for the scrubber chart, from the latest contract's conditions.
    ref_contract = incident.current_contract_id or windows[-1].contract_id
    ref_conditions = conditions_for(ref_contract)
    vib = next((c for c in ref_conditions if c.key == "vibration_rms"), None)
    thresholds = {
        "vibration_max": vib.threshold if vib else None,
        "vibration_baseline": vib.baseline if vib else None,
        "temperature_baseline": next((c.baseline for c in ref_conditions if c.key.startswith("temperature")), None),
    }

    frames: list[dict] = []
    markers: list[dict] = []
    global_index = 0
    apparent_recovery_logged = False
    for w in windows:
        conditions = conditions_for(w.contract_id)
        required = w.required_stable_cycles
        obs = session.exec(
            select(RecoveryObservation).where(RecoveryObservation.window_id == w.id)
            .order_by(RecoveryObservation.cycle_index)  # type: ignore[arg-type]
        ).all()
        streak = 0
        for o in obs:
            global_index += 1
            stable = is_stable_observation(o, conditions)
            streak = streak + 1 if stable else 0
            if o.fault_code:
                markers.append({"index": global_index, "window": w.sequence, "cycle": o.cycle_index,
                                "kind": "relapse", "label": f"Fault {o.fault_code} recurred"})
            elif streak >= required and not apparent_recovery_logged:
                markers.append({"index": global_index, "window": w.sequence, "cycle": o.cycle_index,
                                "kind": "window_complete", "label": f"{required} stable cycles reached"})
                apparent_recovery_logged = True
            frames.append({
                "index": global_index,
                "window": w.sequence,
                "cycle": o.cycle_index,
                "vibration": o.vibration,
                "temperature": o.temperature,
                "cycle_time": o.cycle_time,
                "scrap_pct": o.scrap_pct,
                "fault_code": o.fault_code,
                "bearing_precursor": o.bearing_precursor,
                "stable": stable,
                "stable_streak": streak,
                "source": o.source,
                "at": _iso(o.at),
            })

    last = frames[-1] if frames else None
    summary = (
        f"{len(frames)} cycle(s) across {len(windows)} window(s). "
        + (f"Peak stable streak reached {max((f['stable_streak'] for f in frames), default=0)}/{required}. "
           if frames else "")
        + (f"{len([m for m in markers if m['kind'] == 'relapse'])} relapse(s) recorded."
           if markers else "No relapse recorded.")
    )
    return {
        "available": True,
        "incident_id": incident.id,
        "required_stable_cycles": required,
        "thresholds": thresholds,
        "frames": frames,
        "markers": markers,
        "final_streak": last["stable_streak"] if last else 0,
        "reopened_count": incident.reopened_count,
        "state": incident.state.value,
        "summary": summary,
        "basis": ("A read-only replay of recorded observations. The stable-cycle streak is recomputed exactly "
                  "as the deterministic evaluator computed it, so the scrub matches the verdict."),
    }
