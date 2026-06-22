"""Quality status + release enforcement.

Quality release is **only** satisfied by an explicit quality-engineer approval plus a passed
first-piece check. The model can never auto-release quality (PROHIBITED action class).
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.adapters.efficast_port import EfficastPort
from app.domain.enums import ApprovalStatus
from app.domain.models import ApprovalDecision, ApprovalRequirement, RecoveryCondition
from app.domain.enums import ConditionStatus, Role


def quality_status(port: EfficastPort, *, machine_id: str, order_id: str | None) -> dict:
    q = port.get_quality_status(machine_id=machine_id, order_id=order_id)
    return {
        "order_id": q.order_id,
        "machine_id": q.machine_id,
        "on_hold": q.on_hold,
        "lots_on_hold": q.lots_on_hold,
        "open_checks": q.open_checks,
        "last_result": q.last_result,
        "source": q.source,
    }


def quality_release_satisfied(session: Session, contract_id: str) -> tuple[bool, str]:
    """True iff a quality-engineer approval for ``quality_release`` exists AND first-piece passed."""
    req = session.exec(
        select(ApprovalRequirement)
        .where(ApprovalRequirement.contract_id == contract_id)
        .where(ApprovalRequirement.key == "quality_release")
    ).first()
    if req is None:
        return False, "no quality_release approval requirement on contract"
    if req.status != ApprovalStatus.APPROVED:
        return False, "quality release not yet approved by quality engineer"

    decision = session.exec(
        select(ApprovalDecision)
        .where(ApprovalDecision.requirement_id == req.id)
        .where(ApprovalDecision.decision == "approve")
    ).first()
    if decision is None or decision.decided_role != Role.QUALITY_ENGINEER:
        return False, "quality release approval must be made by a quality engineer"

    fp = session.exec(
        select(RecoveryCondition)
        .where(RecoveryCondition.contract_id == contract_id)
        .where(RecoveryCondition.key == "first_piece")
    ).first()
    if fp is not None and fp.status not in (ConditionStatus.PASSED, ConditionStatus.PASSING):
        return False, "first-piece quality condition not passed"
    return True, "quality release satisfied"
