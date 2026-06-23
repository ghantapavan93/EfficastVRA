"""Notification dispatch — push the next task to the right person/role.

Solves the core pain directly: personnel should not have to hunt across siloed systems for what to do
next. The agent emits a notification when it needs human evidence, an approval, or when it reopens,
verifies, or escalates an incident. The prototype channel is in-app (read at /api/notifications); a
real deployment swaps the sink for Efficast's WhatsApp/email — this function is the NotificationPort
seam.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlmodel import Session, select

from app.config import get_settings
from app.domain.enums import Role
from app.domain.models import Incident, Notification

log = logging.getLogger("vra")
_settings = get_settings()


def dispatch(
    session: Session,
    *,
    to_role: Role,
    kind: str,
    title: str,
    body: str,
    incident: Optional[Incident] = None,
    correlation_id: str = "",
    channel: str = "in_app",
    to_user: Optional[str] = None,
    action_path: str = "",
) -> Notification:
    note = Notification(
        tenant_id=_settings.tenant_id,
        plant_id=incident.plant_id if incident else _settings.plant_id,
        incident_id=incident.id if incident else None,
        correlation_id=correlation_id or (incident.correlation_id if incident else ""),
        to_role=to_role,
        to_user=to_user,
        channel=channel,
        kind=kind,
        title=title,
        body=body,
        status="unread",
        action_path=action_path or (f"/missions/{incident.id}" if incident else ""),
    )
    session.add(note)
    session.flush()
    log.info('notification kind=%s to_role=%s incident=%s', kind, to_role.value, note.incident_id)
    return note


def list_for(session: Session, *, role: Optional[Role] = None, limit: int = 50) -> list[Notification]:
    q = select(Notification).order_by(Notification.created_at.desc())  # type: ignore[attr-defined]
    if role is not None:
        q = q.where(Notification.to_role == role)
    return session.exec(q.limit(limit)).all()


def mark_read(session: Session, notification_id: str) -> Optional[Notification]:
    note = session.get(Notification, notification_id)
    if note is not None:
        note.status = "read"
        session.add(note)
        session.flush()
    return note


def unread_count(session: Session, *, role: Optional[Role] = None) -> int:
    q = select(Notification).where(Notification.status == "unread")
    if role is not None:
        q = q.where(Notification.to_role == role)
    return len(session.exec(q).all())
