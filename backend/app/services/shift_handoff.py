"""Persisted shift handoff — the incoming shift inherits the full picture, not a re-derivation.

Recovery missions outlive a single shift. This freezes a point-in-time snapshot of every open mission
(where it stands, who must act next, what's blocking, whether it reopened) into a durable record the next
shift acknowledges. It is documentation, not a recovery side-effect: it changes no mission state, grants
nothing, and touches no machine — so it persists directly (with an audit entry), not through the gateway.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.auth import Principal
from app.domain.base import utcnow
from app.domain.enums import AuditEventType
from app.domain.models import Incident, ShiftHandoff
from app.services.mission_spine import assess_mission
from app.workflow.audit import record_audit

_TERMINAL = {"VERIFIED_RECOVERY", "CANCELLED", "ESCALATED", "INSUFFICIENT_EVIDENCE"}


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _snapshot(session: Session, incident: Incident) -> dict:
    spine = assess_mission(session, incident)
    return {
        "id": incident.id,
        "title": incident.title,
        "fault_code": incident.fault_code,
        "state": incident.state.value,
        "stage": spine.get("current_stage"),
        "who_next": spine.get("who_next"),
        "what_blocks": spine.get("what_blocks"),
        "reopened_count": incident.reopened_count,
        "outcome": spine.get("outcome"),
    }


def _headline(stats: dict) -> str:
    n = stats["open_missions"]
    if n == 0:
        return "No open recovery missions — clean handoff."
    parts = [f"{n} open mission{'s' if n != 1 else ''}"]
    if stats["reopened"]:
        parts.append(f"{stats['reopened']} reopened")
    if stats["awaiting_human"]:
        parts.append(f"{stats['awaiting_human']} awaiting a human decision")
    return ", ".join(parts) + "."


def build_preview(session: Session, plant_id: Optional[str] = None) -> dict:
    """The live state that *would* be handed off right now — read-only."""
    incidents = session.exec(select(Incident).where(Incident.historical == False)).all()  # noqa: E712
    active = [i for i in incidents
             if i.state.value not in _TERMINAL and (plant_id is None or i.plant_id == plant_id)]
    snaps = [_snapshot(session, i) for i in active]
    stats = {
        "open_missions": len(snaps),
        "reopened": sum(1 for s in snaps if s["reopened_count"] > 0),
        "awaiting_human": sum(1 for s in snaps if "APPROVAL" in s["state"] or "AWAITING" in s["state"]),
        "monitoring": sum(1 for s in snaps if s["state"] == "MONITORING_RECOVERY"),
    }
    return {"open_missions": snaps, "stats": stats, "headline": _headline(stats),
            "basis": "A read-only snapshot of open missions (state + who's next + what's blocking) at this moment."}


def _view(h: ShiftHandoff) -> dict:
    return {
        "id": h.id, "from_shift": h.from_shift, "to_shift": h.to_shift,
        "created_by": h.created_by, "created_role": h.created_role.value, "created_at": _iso(h.created_at),
        "headline": h.headline, "notes": h.notes, "open_missions": h.open_missions, "stats": h.stats,
        "acknowledged_by": h.acknowledged_by, "acknowledged_at": _iso(h.acknowledged_at),
    }


def create_handoff(session: Session, principal: Principal, *, from_shift: str = "", to_shift: str = "",
                   notes: str = "") -> dict:
    preview = build_preview(session, principal.plant_id)
    h = ShiftHandoff(
        tenant_id=principal.tenant_id, plant_id=principal.plant_id,
        from_shift=from_shift, to_shift=to_shift, created_by=principal.username, created_role=principal.role,
        headline=preview["headline"], notes=notes,
        open_missions=preview["open_missions"], stats=preview["stats"],
    )
    session.add(h)
    session.flush()
    record_audit(
        session, type=AuditEventType.SHIFT_HANDOFF, correlation_id=f"handoff-{principal.plant_id}",
        actor=principal.username, role=principal.role, plant_id=principal.plant_id,
        summary=f"Shift handoff {from_shift or '?'}→{to_shift or '?'}: {preview['headline']}",
        detail={"handoff_id": h.id, "notes": notes, **preview["stats"]},
    )
    session.flush()
    return _view(h)


def list_handoffs(session: Session, plant_id: Optional[str] = None, *, limit: int = 20) -> dict:
    rows = session.exec(
        select(ShiftHandoff).order_by(ShiftHandoff.created_at.desc())  # type: ignore[attr-defined]
    ).all()
    if plant_id:
        rows = [r for r in rows if r.plant_id == plant_id]
    return {"handoffs": [_view(r) for r in rows[:limit]]}


def acknowledge(session: Session, handoff_id: str, principal: Principal) -> Optional[dict]:
    h = session.get(ShiftHandoff, handoff_id)
    if h is None:
        return None
    if h.acknowledged_by is None:
        h.acknowledged_by = principal.username
        h.acknowledged_at = utcnow()
        session.add(h)
        session.flush()
        record_audit(
            session, type=AuditEventType.SHIFT_HANDOFF, correlation_id=f"handoff-{h.plant_id}",
            actor=principal.username, role=principal.role, plant_id=h.plant_id,
            summary=f"Shift handoff {h.id} acknowledged by {principal.username}",
            detail={"handoff_id": h.id, "acknowledged": True},
        )
        session.flush()
    return _view(h)
