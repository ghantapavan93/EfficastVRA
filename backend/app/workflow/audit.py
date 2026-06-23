"""Audit trail + transactional outbox helpers.

Every meaningful event is appended to :class:`AuditEvent` with a monotonic per-correlation ``seq``,
stamped with policy/workflow/model/prompt versions. Outbox events are written in the *same*
transaction as the state change they describe, then published by a worker — so a crash can never
drop or duplicate a published decision.
"""

from __future__ import annotations

import hashlib
import json
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.config import get_settings
from app.domain.base import utcnow
from app.domain.enums import AuditEventType, Role, WorkflowState
from app.domain.models import AuditEvent, OutboxEvent

_settings = get_settings()


def next_seq(session: Session, correlation_id: str) -> int:
    current = session.exec(
        select(func.max(AuditEvent.seq)).where(AuditEvent.correlation_id == correlation_id)
    ).first()
    return (current or 0) + 1


def _entry_hash(prev_hash: str, *, seq: int, type_: str, actor: str, role: str, summary: str,
                prev_state: Optional[str], new_state: Optional[str], detail: dict) -> str:
    """Deterministic content hash, chained to the previous entry — tamper-evidence for the audit log."""
    canon = json.dumps(
        {"prev": prev_hash, "seq": seq, "type": type_, "actor": actor, "role": role,
         "summary": summary, "prev_state": prev_state, "new_state": new_state, "detail": detail},
        sort_keys=True, default=str, separators=(",", ":"),
    )
    return hashlib.sha256(canon.encode()).hexdigest()


def verify_audit_chain(session: Session, correlation_id: str) -> dict:
    """Recompute the per-correlation hash chain and report whether it is intact (no row was altered,
    inserted, or removed). Detects tampering at the first broken sequence number."""
    events = session.exec(
        select(AuditEvent).where(AuditEvent.correlation_id == correlation_id)
        .order_by(AuditEvent.seq)  # type: ignore[arg-type]
    ).all()
    prev = ""
    for ev in events:
        expected = _entry_hash(
            prev, seq=ev.seq, type_=ev.type.value, actor=ev.actor, role=ev.role.value,
            summary=ev.summary, prev_state=ev.prev_state.value if ev.prev_state else None,
            new_state=ev.new_state.value if ev.new_state else None, detail=ev.detail or {},
        )
        if ev.prev_hash != prev or ev.entry_hash != expected:
            return {"ok": False, "broken_at_seq": ev.seq, "count": len(events)}
        prev = ev.entry_hash
    return {"ok": True, "broken_at_seq": None, "count": len(events)}


def record_audit(
    session: Session,
    *,
    type: AuditEventType,
    correlation_id: str,
    actor: str,
    role: Role,
    summary: str,
    plant_id: Optional[str] = None,
    incident_id: Optional[str] = None,
    contract_id: Optional[str] = None,
    detail: Optional[dict] = None,
    prev_state: Optional[WorkflowState] = None,
    new_state: Optional[WorkflowState] = None,
    model_version: str = "",
    prompt_version: str = "",
) -> AuditEvent:
    last = session.exec(
        select(AuditEvent).where(AuditEvent.correlation_id == correlation_id)
        .order_by(AuditEvent.seq.desc())  # type: ignore[attr-defined]
    ).first()
    seq = (last.seq if last else 0) + 1
    prev_hash = last.entry_hash if last else ""
    entry_hash = _entry_hash(
        prev_hash, seq=seq, type_=type.value, actor=actor, role=role.value, summary=summary,
        prev_state=prev_state.value if prev_state else None,
        new_state=new_state.value if new_state else None, detail=detail or {},
    )
    ev = AuditEvent(
        tenant_id=_settings.tenant_id,
        plant_id=plant_id or _settings.plant_id,
        correlation_id=correlation_id,
        incident_id=incident_id,
        contract_id=contract_id,
        seq=seq,
        type=type,
        actor=actor,
        role=role,
        summary=summary,
        detail=detail or {},
        prev_state=prev_state,
        new_state=new_state,
        policy_version=_settings.policy_version,
        workflow_version=_settings.workflow_version,
        model_version=model_version,
        prompt_version=prompt_version,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )
    session.add(ev)
    session.flush()
    return ev


def publish_outbox(session: Session, *, topic: str, payload: dict, correlation_id: str) -> OutboxEvent:
    evt = OutboxEvent(
        tenant_id=_settings.tenant_id,
        topic=topic,
        payload=payload,
        correlation_id=correlation_id,
        status="pending",
        available_at=utcnow(),
    )
    session.add(evt)
    session.flush()
    return evt


MAX_OUTBOX_ATTEMPTS = 5


def drain_outbox(session: Session, *, limit: int = 200, sink=None) -> int:
    """Relay pending outbox events to the publish sink and mark them published.

    This is the read side of the transactional-outbox pattern: events are written in the same
    transaction as the state change (so a crash can never lose them), then published exactly once by
    this relay. A real deployment would run it on a loop / a worker against a broker; here the default
    sink is a no-op log. Failures are classified — retried until ``MAX_OUTBOX_ATTEMPTS``, then parked
    as ``failed`` (a dead-letter state) so they never block the queue.
    """
    now = utcnow()
    pending = session.exec(
        select(OutboxEvent)
        .where(OutboxEvent.status == "pending")
        .where((OutboxEvent.available_at == None) | (OutboxEvent.available_at <= now))  # noqa: E711
        .order_by(OutboxEvent.available_at, OutboxEvent.id)  # type: ignore[arg-type]  # stable tie-break
        .limit(limit)
    ).all()
    published = 0
    for evt in pending:
        evt.attempts += 1
        try:
            if sink is not None:
                sink(evt.topic, evt.payload, evt.correlation_id)
            evt.status = "published"
            evt.published_at = utcnow()
            evt.last_error = ""
            published += 1
        except Exception as exc:  # retry classification + dead-letter
            evt.last_error = str(exc)[:500]
            evt.status = "failed" if evt.attempts >= MAX_OUTBOX_ATTEMPTS else "pending"
        session.add(evt)
    session.flush()
    return published


def outbox_stats(session: Session) -> dict:
    rows = session.exec(select(OutboxEvent.status)).all()
    stats = {"pending": 0, "published": 0, "failed": 0}
    for s in rows:
        stats[s] = stats.get(s, 0) + 1
    return stats
