"""Persistence for the agent's reasoning trace.

Every node of the bounded agent graph records one ``AgentReasoningTrace`` row so the agent's reasoning
is fully inspectable and auditable. These rows are *evidence of reasoning*; they never grant
permissions or decide recovery (see docs/AGENT_RESEARCH.md).
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.domain.models import AgentReasoningTrace, Incident


def _next_seq(session: Session, incident_id: str) -> int:
    cur = session.exec(
        select(func.max(AgentReasoningTrace.seq)).where(
            AgentReasoningTrace.incident_id == incident_id
        )
    ).one()
    return int(cur or 0) + 1


def record_trace(
    session: Session,
    *,
    incident: Incident,
    node: str,
    title: str,
    rationale: str,
    inputs: Optional[dict[str, Any]] = None,
    outputs: Optional[dict[str, Any]] = None,
    citations: Optional[list[dict]] = None,
    confidence: Optional[float] = None,
    revision: int = 0,
    contract_id: Optional[str] = None,
    model_version: str = "",
    prompt_version: str = "",
) -> AgentReasoningTrace:
    """Append one reasoning step. Flushed immediately so ``seq`` stays monotonic within the tx."""
    trace = AgentReasoningTrace(
        tenant_id=incident.tenant_id,
        plant_id=incident.plant_id,
        incident_id=incident.id,
        contract_id=contract_id,
        correlation_id=incident.correlation_id,
        seq=_next_seq(session, incident.id),
        node=node,
        title=title,
        rationale=rationale,
        inputs=inputs or {},
        outputs=outputs or {},
        citations=citations or [],
        confidence=confidence,
        revision=revision,
        model_version=model_version,
        prompt_version=prompt_version,
    )
    session.add(trace)
    session.flush()
    return trace


def list_traces(session: Session, incident_id: str) -> list[AgentReasoningTrace]:
    return session.exec(
        select(AgentReasoningTrace)
        .where(AgentReasoningTrace.incident_id == incident_id)
        .order_by(AgentReasoningTrace.seq)  # type: ignore[arg-type]
    ).all()


def latest_confidence(session: Session, incident_id: str) -> Optional[float]:
    """Most recent (heuristic, uncalibrated) confidence the agent emitted for this incident, if any."""
    row = session.exec(
        select(AgentReasoningTrace)
        .where(AgentReasoningTrace.incident_id == incident_id)
        .where(AgentReasoningTrace.confidence.is_not(None))  # type: ignore[union-attr]
        .order_by(AgentReasoningTrace.seq.desc())  # type: ignore[attr-defined]
    ).first()
    return row.confidence if row else None
