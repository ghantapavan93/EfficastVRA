"""Reusable flow helpers for tests."""

from __future__ import annotations

from sqlmodel import Session, select

from app.auth import Principal
from app.domain.models import ApprovalRequirement, EvidenceRequirement, Incident, RecoveryContract, User
from app.seed.northstar import IDS
from app.workflow.recovery_service import RecoveryService


def principal(session: Session, username: str) -> Principal:
    u = session.exec(select(User).where(User.username == username)).first()
    return Principal(u.id, u.username, u.role, u.plant_id, u.tenant_id)


def req_id(session: Session, contract_id: str, key: str) -> str:
    r = session.exec(select(EvidenceRequirement).where(EvidenceRequirement.contract_id == contract_id)
                     .where(EvidenceRequirement.key == key)).first()
    return r.id


def appr_id(session: Session, contract_id: str, key: str) -> str:
    r = session.exec(select(ApprovalRequirement).where(ApprovalRequirement.contract_id == contract_id)
                     .where(ApprovalRequirement.key == key)).first()
    return r.id


def to_monitoring(session: Session) -> tuple[RecoveryService, Incident, RecoveryContract]:
    """Draft → evidence → approve → start monitoring. Returns at MONITORING_RECOVERY (window 1)."""
    svc = RecoveryService(session)
    inc = session.get(Incident, IDS["incident"])
    sup = principal(session, "s.vega")
    tech = principal(session, "a.lang")
    c1 = svc.draft_contract(inc)
    svc.review_contract(inc, sup)
    svc.submit_evidence(inc, tech, requirement_id=req_id(session, c1.id, "post_alignment_measurement"),
                        value_num=3.6, unit="mm/s")
    svc.submit_evidence(inc, tech, requirement_id=req_id(session, c1.id, "technician_completion"),
                        value_text="completed")
    svc.record_approval(inc, sup, requirement_id=appr_id(session, c1.id, "contract_review"))
    svc.start_monitoring(inc)
    return svc, inc, c1


def to_reopened(session: Session) -> tuple[RecoveryService, Incident]:
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 17)  # triggers reopen at cycle 17
    session.refresh(inc)
    return svc, inc


def to_window2_stable(session: Session, cycles: int = 30) -> tuple[RecoveryService, Incident, RecoveryContract]:
    svc, inc = to_reopened(session)
    sup = principal(session, "s.vega")
    tech = principal(session, "a.lang")
    svc.approve_contingency(inc, sup)
    c2 = svc._contract(inc)
    svc.submit_evidence(inc, tech, requirement_id=req_id(session, c2.id, "bearing_post_measurement"),
                        value_num=3.1, unit="mm/s")
    svc.submit_evidence(inc, tech, requirement_id=req_id(session, c2.id, "technician_completion_2"),
                        value_text="completed")
    svc.complete_contingency(inc)
    svc.advance(inc, cycles)
    return svc, inc, c2


def to_quality_released(session: Session, cycles: int = 30) -> tuple[RecoveryService, Incident, RecoveryContract]:
    """Reach a verified-ELIGIBLE state on the bearing contract: ``cycles`` stable cycles + first-piece +
    quality release, but NOT yet finalized — so ``finalize`` can be called/observed under the ceiling.
    The evaluator verdict is 'verified'; only finalize() (the comparable-conditions gate) decides closure."""
    svc, inc, c2 = to_window2_stable(session, cycles=cycles)
    qual = principal(session, "q.idris")
    svc.submit_evidence(inc, qual, requirement_id=req_id(session, c2.id, "first_piece_quality"),
                        value_text="pass")
    svc.record_approval(inc, qual, requirement_id=appr_id(session, c2.id, "quality_release"),
                        reason="first-piece passed; lots dispositioned")
    return svc, inc, c2
