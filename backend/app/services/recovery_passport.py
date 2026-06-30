"""Recovery Passport — an asset's verified-recovery history, as one read-only record.

Every incident is a moment; the Passport is the *asset's memory*: how many times this machine's apparent
recovery was rejected before a work order could falsely close it, how often recovery actually held, how long
it took. It is a pure projection over incidents/outcomes — it decides nothing and changes no state.

The headline metric is ``false_closures_caught``: the count of times the agent refused to let "work order
closed" stand in for "line recovered" on this asset. That number is the product, per machine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.domain.enums import WorkflowState
from app.domain.models import Incident, Machine

_TERMINAL = {"VERIFIED_RECOVERY", "CANCELLED", "ESCALATED", "INSUFFICIENT_EVIDENCE"}


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _caught_false_closure(inc: Incident) -> bool:
    """A false closure was caught iff recovery was reopened after an apparent fix, or the upload's
    reconstruction flagged a relapse the closed work order had missed."""
    if inc.reopened_count > 0:
        return True
    intake = getattr(inc, "intake", None) or {}
    return bool((intake.get("reconstruction") or {}).get("false_closure_detected"))


def _entry(inc: Incident) -> dict:
    intake = getattr(inc, "intake", None) or {}
    dur = None
    if inc.closed_at and inc.opened_at:
        dur = (inc.closed_at - inc.opened_at).total_seconds()
    return {
        "id": inc.id,
        "title": inc.title,
        "fault_code": inc.fault_code,
        "severity": inc.severity.value,
        "state": inc.state.value,
        "outcome": inc.outcome_type.value if inc.outcome_type else None,
        "outcome_summary": inc.outcome_summary,
        "reopened_count": inc.reopened_count,
        "false_closure_caught": _caught_false_closure(inc),
        "from_upload": bool(intake),
        "historical": inc.historical,
        "is_active": inc.state.value not in _TERMINAL,
        "opened_at": _iso(inc.opened_at),
        "closed_at": _iso(inc.closed_at),
        "duration_hours": round(dur / 3600, 1) if dur else None,
    }


def list_assets(session: Session) -> dict:
    """Every machine with a one-line recovery footprint — the picker for the Passport."""
    machines = session.exec(select(Machine)).all()
    assets = []
    for m in machines:
        incs = session.exec(select(Incident).where(Incident.machine_id == m.id)).all()
        assets.append({
            "id": m.id, "code": m.code, "name": m.name, "machine_model": m.machine_model,
            "mission_count": len(incs),
            "false_closures_caught": sum(1 for i in incs if _caught_false_closure(i)),
            "verified": sum(1 for i in incs if i.state == WorkflowState.VERIFIED_RECOVERY),
            "active": sum(1 for i in incs if i.state.value not in _TERMINAL),
        })
    assets.sort(key=lambda a: (-a["mission_count"], a["code"]))
    return {"assets": assets}


def build_passport(session: Session, machine_id: str) -> dict:
    machine = session.get(Machine, machine_id)
    if machine is None:
        return {"available": False, "reason": "asset not found"}
    incidents = session.exec(
        select(Incident).where(Incident.machine_id == machine_id)
        .order_by(Incident.opened_at)  # type: ignore[arg-type]
    ).all()

    entries = [_entry(i) for i in incidents]
    total = len(entries)
    verified = sum(1 for e in entries if e["state"] == "VERIFIED_RECOVERY")
    durations = [e["duration_hours"] for e in entries if e["duration_hours"] is not None]
    stats = {
        "total_missions": total,
        "verified": verified,
        "verified_rate": round(100 * verified / total) if total else 0,
        "reopened_missions": sum(1 for e in entries if e["reopened_count"] > 0),
        "reopens_total": sum(e["reopened_count"] for e in entries),
        "false_closures_caught": sum(1 for e in entries if e["false_closure_caught"]),
        "insufficient": sum(1 for e in entries if e["outcome"] == "INSUFFICIENT_EVIDENCE"),
        "escalated": sum(1 for e in entries if e["outcome"] == "ESCALATED"),
        "active_missions": sum(1 for e in entries if e["is_active"]),
        "from_upload": sum(1 for e in entries if e["from_upload"]),
        "mean_time_to_outcome_hours": round(sum(durations) / len(durations), 1) if durations else None,
    }
    return {
        "available": True,
        "machine": {"id": machine.id, "code": machine.code, "name": machine.name,
                    "machine_model": machine.machine_model, "manufacturer": machine.manufacturer,
                    "state": machine.state.value, "baseline": machine.baseline, "live": machine.live},
        "stats": stats,
        "entries": list(reversed(entries)),  # most recent first
        "basis": ("A read-only projection over this asset's incidents and their deterministic outcomes. "
                  "'False closures caught' counts the times recovery was reopened after an apparent fix or a "
                  "relapse was found in uploaded data — the times a closed work order would have been wrong."),
    }
