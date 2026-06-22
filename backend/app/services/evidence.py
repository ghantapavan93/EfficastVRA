"""Evidence validation: freshness, validity rules, and requirement satisfaction.

A condition can only be satisfied by **fresh, valid, role-appropriate** evidence. Stale telemetry or
a wrong-role submission cannot satisfy a requirement — enforced here, asserted by tests.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from app.domain.base import utcnow
from app.domain.enums import EvidenceStatus
from app.domain.models import EvidenceItem, EvidenceRequirement


def compute_freshness(item: EvidenceItem) -> int:
    if item.evidence_timestamp is None:
        return 0
    base = item.received_at or utcnow()
    return max(int((base - item.evidence_timestamp).total_seconds()), 0)


def validate_item(item: EvidenceItem, requirement: EvidenceRequirement) -> EvidenceItem:
    """Set ``freshness_s``, ``valid`` and ``status`` on a submitted item per the requirement."""
    item.freshness_s = compute_freshness(item)

    # Role must match the requirement's assigned role (defence in depth; gateway also checks).
    if item.submitted_role != requirement.assigned_role:
        item.valid = False
        item.status = EvidenceStatus.REJECTED
        item.conflict_reason = (
            f"submitted by role {item.submitted_role.value}, requires {requirement.assigned_role.value}"
        )
        return item

    # Freshness gate
    if requirement.freshness_max_s is not None and item.freshness_s > requirement.freshness_max_s:
        item.valid = False
        item.status = EvidenceStatus.EXPIRED
        item.conflict_reason = (
            f"stale: {item.freshness_s}s old > max {requirement.freshness_max_s}s"
        )
        return item

    # Validity rule
    rule = requirement.validity_rule or {}
    rtype = rule.get("type", "present")
    ok = True
    reason = ""
    if rtype == "numeric":
        v = item.value_num
        lo, hi = rule.get("min"), rule.get("max")
        if v is None:
            ok, reason = False, "no numeric value"
        elif lo is not None and v < lo:
            ok, reason = False, f"{v} < min {lo}"
        elif hi is not None and v > hi:
            ok, reason = False, f"{v} > max {hi}"
    elif rtype == "pass_fail":
        expect = rule.get("expect", "pass")
        got = (item.value_text or "").strip().lower() or ("pass" if item.value_num == 1 else "fail")
        ok = got == expect
        reason = "" if ok else f"expected {expect}, got {got}"
    elif rtype == "approval":
        got = (item.value_text or "").strip().lower()
        ok = got in {"approve", "approved", "yes", "true"}
        reason = "" if ok else "not an approval"
    # rtype == "present": any submission counts

    item.valid = ok
    item.status = EvidenceStatus.VALIDATED if ok else EvidenceStatus.REJECTED
    if not ok:
        item.conflict_reason = reason
    return item


def latest_valid_item(session: Session, requirement_id: str) -> Optional[EvidenceItem]:
    items = session.exec(
        select(EvidenceItem)
        .where(EvidenceItem.requirement_id == requirement_id)
        .order_by(EvidenceItem.received_at.desc())  # type: ignore[attr-defined]
    ).all()
    for it in items:
        if it.valid and it.status == EvidenceStatus.VALIDATED:
            return it
    return None


def requirement_satisfied(session: Session, requirement: EvidenceRequirement) -> bool:
    return latest_valid_item(session, requirement.id) is not None


def missing_required(session: Session, contract_id: str, phase: str) -> list[EvidenceRequirement]:
    """Requirements for ``phase`` (monitoring|closure|quality_release) not yet satisfied."""
    reqs = session.exec(
        select(EvidenceRequirement)
        .where(EvidenceRequirement.contract_id == contract_id)
        .where(EvidenceRequirement.required_before == phase)
    ).all()
    return [r for r in reqs if not requirement_satisfied(session, r)]
