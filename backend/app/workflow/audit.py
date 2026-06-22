"""Audit trail + transactional outbox helpers.

Every meaningful event is appended to :class:`AuditEvent` with a monotonic per-correlation ``seq``,
stamped with policy/workflow/model/prompt versions. Outbox events are written in the *same*
transaction as the state change they describe, then published by a worker — so a crash can never
drop or duplicate a published decision.
"""

from __future__ import annotations

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
    ev = AuditEvent(
        tenant_id=_settings.tenant_id,
        plant_id=plant_id or _settings.plant_id,
        correlation_id=correlation_id,
        incident_id=incident_id,
        contract_id=contract_id,
        seq=next_seq(session, correlation_id),
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
