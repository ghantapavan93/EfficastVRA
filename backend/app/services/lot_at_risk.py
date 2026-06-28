"""Lot-at-Risk analysis — the thesis at the product level: a closed work order ≠ good product.

When a fault occurred during a window, the lots produced across the questionable span may not be good. This
read-only analysis identifies the last known-good cycle, the first questionable cycle, the affected
production window, the affected lots + their current disposition, and the required quality action — as a
**recommendation only**. It NEVER auto-releases or quarantines product (the frozen no-auto-quality-release
rule); a Material Review Board / quality engineer owns that decision.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from app.domain.models import Incident, MaterialLot, RecoveryObservation


def _iso(dt) -> Optional[str]:
    return dt.isoformat() if dt else None


def assess_lot_at_risk(session: Session, incident: Incident) -> dict:
    obs = session.exec(
        select(RecoveryObservation).where(RecoveryObservation.incident_id == incident.id)
        .order_by(RecoveryObservation.at)  # type: ignore[arg-type]
    ).all()
    questionable = next((o for o in obs if o.fault_code), None)
    if questionable is None:
        return {"available": True, "incident_id": incident.id, "at_risk": False,
                "summary": "No questionable cycle observed in this incident — no lots flagged at risk."}

    idx = obs.index(questionable)
    last_good = obs[idx - 1] if idx > 0 else None
    affected_from = (last_good.at if last_good else questionable.at)
    affected_to = incident.closed_at or (obs[-1].at if obs else questionable.at)

    lots = (session.exec(select(MaterialLot).where(MaterialLot.order_id == incident.order_id)).all()
            if incident.order_id else [])

    def overlaps(lot: MaterialLot) -> bool:
        # conservative: a lot with an unknown production window is *possibly* affected → include it
        return ((lot.produced_from is None or lot.produced_from <= affected_to)
                and (lot.produced_to is None or lot.produced_to >= affected_from))

    affected = [lot for lot in lots if overlaps(lot)]
    return {
        "available": True,
        "incident_id": incident.id,
        "at_risk": True,
        "last_good_cycle": (last_good.cycle_index if last_good else None),
        "first_questionable_cycle": questionable.cycle_index,
        "fault_code": questionable.fault_code,
        "affected_window": {"from": _iso(affected_from), "to": _iso(affected_to)},
        "affected_lots": [{"id": lot.id, "disposition": lot.disposition.value,
                           "produced_from": _iso(lot.produced_from), "produced_to": _iso(lot.produced_to)}
                          for lot in affected],
        "affected_lot_count": len(affected),
        "current_dispositions": sorted({lot.disposition.value for lot in affected}),
        "affected_quantity_note": "Per-lot quantity is held in the MES, not this prototype's lot model.",
        "required_quality_action": (
            "Quarantine the affected lot(s) and route to a Material Review Board (MRB) for disposition "
            "(use-as-is / rework / scrap). RECOMMENDATION only — the system never auto-releases or "
            "quarantines product; a quality engineer decides."),
        "basis": ("Read-only. Operationalises 'a closed work order ≠ a recovered line' at the product level: "
                  "lots produced during the questionable window may not be good. Never changes a lot "
                  "disposition. Synthetic PROTOTYPE_ASSUMPTION."),
    }
