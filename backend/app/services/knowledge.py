"""Knowledge review & learning loop — turn a one-off recovery into institutional memory.

Closes the brief's hardest pain — *translating tribal knowledge into something the next shift can use*
— with the pattern 2026 research endorses for production agents: **human-as-judge curated memory**
(continual learning by curating a knowledge base, not by retraining weights, so there is no
catastrophic forgetting). The flow:

    verified recovery → agent drafts a KnowledgeCandidate (PENDING_REVIEW)
                      → the required reviewer role approves/rejects it (human judges if it generalises)
                      → APPROVED lessons become authoritative and surface in Troubleshooting for the
                        next shift / a sibling machine.

The agent proposes the lesson; a human curates it; only curated knowledge is shown as authoritative.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from app.auth import Principal
from app.domain.base import utcnow
from app.domain.enums import AuditEventType, KnowledgeStatus, Role
from app.domain.models import Incident, KnowledgeCandidate
from app.workflow.audit import record_audit
from app.workflow.recovery_service import WorkflowError


def list_candidates(session: Session, *, status: Optional[KnowledgeStatus] = None) -> list[KnowledgeCandidate]:
    q = select(KnowledgeCandidate).order_by(KnowledgeCandidate.created_at.desc())  # type: ignore[attr-defined]
    if status is not None:
        q = q.where(KnowledgeCandidate.status == status)
    return session.exec(q).all()


def review_knowledge(session: Session, candidate_id: str, principal: Principal, *,
                     decision: str, reason: str = "") -> KnowledgeCandidate:
    """Approve or reject a knowledge candidate. Only the required reviewer role (or a plant admin) may
    curate it — the agent can never approve its own lesson into authoritative guidance."""
    kc = session.get(KnowledgeCandidate, candidate_id)
    if kc is None:
        raise WorkflowError("knowledge candidate not found", code="not_found", status_code=404)
    if principal.role not in (kc.reviewer_role, Role.PLANT_ADMIN):
        raise WorkflowError(
            f"role {principal.role.value} may not review knowledge (requires {kc.reviewer_role.value})",
            code="role_denied", status_code=403,
        )
    if kc.status != KnowledgeStatus.PENDING_REVIEW:
        raise WorkflowError(f"candidate already {kc.status.value.lower()}", code="already_reviewed")

    kc.status = KnowledgeStatus.APPROVED if decision == "approve" else KnowledgeStatus.REJECTED
    kc.reviewed_by = principal.username
    kc.reviewed_at = utcnow()
    kc.review_reason = reason
    session.add(kc)

    incident = session.get(Incident, kc.incident_id)
    record_audit(
        session, type=AuditEventType.KNOWLEDGE_REVIEWED,
        correlation_id=incident.correlation_id if incident else kc.id,
        actor=principal.username, role=principal.role,
        summary=f"Knowledge '{kc.title}' {kc.status.value.lower()} by {principal.role.value}",
        incident_id=kc.incident_id, detail={"candidate_id": kc.id, "decision": decision, "reason": reason},
    )
    session.flush()
    return kc
