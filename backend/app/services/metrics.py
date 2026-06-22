"""Recovery metrics (machine + production) — thin deterministic views over the port + DB."""

from __future__ import annotations

from sqlmodel import Session, select

from app.adapters.efficast_port import EfficastPort
from app.domain.base import utcnow
from app.domain.models import DowntimeEvent, ProductionOrder, ScrapEvent


def machine_recovery_metrics(port: EfficastPort, machine_id: str) -> dict:
    snap = port.get_machine_snapshot(machine_id)
    b = snap.baseline or {}

    def cmp(value, base):
        if value is None or base in (None, 0):
            return None
        return round(value - base, 3)

    return {
        "machine_id": machine_id,
        "source": snap.source,
        "timestamp": snap.timestamp.isoformat() if snap.timestamp else None,
        "freshness_s": snap.freshness_s,
        "fault_code": snap.fault_code,
        "metrics": {
            "vibration": {"value": snap.vibration, "baseline": b.get("vibration_mm_s"),
                          "delta": cmp(snap.vibration, b.get("vibration_mm_s")), "unit": "mm/s"},
            "temperature": {"value": snap.temperature, "baseline": b.get("temp_c"),
                            "delta": cmp(snap.temperature, b.get("temp_c")), "unit": "°C"},
            "cycle_time": {"value": snap.cycle_time, "baseline": b.get("cycle_time_s"),
                           "delta": cmp(snap.cycle_time, b.get("cycle_time_s")), "unit": "s"},
            "scrap_pct": {"value": snap.scrap_pct, "baseline": b.get("scrap_pct"),
                          "delta": cmp(snap.scrap_pct, b.get("scrap_pct")), "unit": "%"},
        },
    }


def production_recovery_metrics(session: Session, port: EfficastPort, order_id: str) -> dict:
    order = session.get(ProductionOrder, order_id)
    if order is None:
        raise KeyError(f"order {order_id} not found")
    scrap_events = session.exec(select(ScrapEvent).where(ScrapEvent.order_id == order_id)).all()
    short_stops = session.exec(
        select(DowntimeEvent).where(DowntimeEvent.order_id == order_id).where(DowntimeEvent.fault_code.is_not(None))  # type: ignore[attr-defined]
    ).all()
    impact = port.get_schedule_impact(order_id)
    scrap_units = sum(s.qty for s in scrap_events)
    return {
        "order_id": order_id,
        "product": order.product,
        "qty_total": order.qty_total,
        "qty_done": order.qty_done,
        "qty_remaining": order.qty_remaining,
        "scrap_units_recent": scrap_units,
        "short_stops_recent": len(short_stops),
        "est_minutes_to_complete": impact.est_minutes_lost,
        "due_at": order.due_at.isoformat() if order.due_at else None,
        "at_risk": impact.at_risk,
        "source": impact.source,
        "as_of": utcnow().isoformat(),
    }
