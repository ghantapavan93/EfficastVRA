"""Headless deterministic replay of the full PO-2841 recovery.

Drives the real orchestrator + gateway end to end (no shortcuts): draft → evidence → approve →
monitor → cycle-17 relapse → reopen → contingency → second window → quality release → verified.
Used by ``python -m app.cli demo`` and by the end-to-end test.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.auth import Principal
from app.db import engine
from app.domain.enums import WorkflowState
from app.domain.models import (
    ApprovalRequirement,
    AuditEvent,
    EvidenceRequirement,
    Incident,
    KnowledgeCandidate,
    User,
)
from app.seed.northstar import IDS
from app.workflow.recovery_service import RecoveryService


def _principal(session: Session, username: str) -> Principal:
    u = session.exec(select(User).where(User.username == username)).first()
    if u is None:
        raise RuntimeError(f"user {username} not seeded")
    return Principal(u.id, u.username, u.role, u.plant_id, u.tenant_id)


def _req_id(session: Session, contract_id: str, key: str) -> str:
    r = session.exec(
        select(EvidenceRequirement).where(EvidenceRequirement.contract_id == contract_id)
        .where(EvidenceRequirement.key == key)
    ).first()
    if r is None:
        raise RuntimeError(f"evidence requirement {key} not found")
    return r.id


def _appr_id(session: Session, contract_id: str, key: str) -> str:
    r = session.exec(
        select(ApprovalRequirement).where(ApprovalRequirement.contract_id == contract_id)
        .where(ApprovalRequirement.key == key)
    ).first()
    if r is None:
        raise RuntimeError(f"approval requirement {key} not found")
    return r.id


def run_scenario(session: Session, *, log=print) -> dict:
    svc = RecoveryService(session)
    incident = session.get(Incident, IDS["incident"])
    sup = _principal(session, "s.vega")
    tech = _principal(session, "a.lang")
    qual = _principal(session, "q.idris")

    log(f"① intervention recorded — {incident.state.value}")

    # ② draft contract V1 + request evidence (agent)
    c1 = svc.draft_contract(incident)
    session.commit()
    log(f"② contract drafted {c1.contract_no} v{c1.version} — {incident.state.value}")

    # ③ technician submits evidence; supervisor reviews contract
    svc.review_contract(incident, sup)
    svc.submit_evidence(incident, tech, requirement_id=_req_id(session, c1.id, "post_alignment_measurement"),
                        value_num=3.6, unit="mm/s", source="VIB-L4-01 handheld")
    svc.submit_evidence(incident, tech, requirement_id=_req_id(session, c1.id, "technician_completion"),
                        value_text="completed")
    svc.record_approval(incident, sup, requirement_id=_appr_id(session, c1.id, "contract_review"),
                        reason="conditions reasonable; begin monitoring")
    session.commit()
    log(f"③ evidence submitted + contract approved — {incident.state.value}")

    # ④ start monitoring (window 1)
    svc.start_monitoring(incident)
    session.commit()
    log(f"④ monitoring started — {incident.state.value}")

    # ⑤ 16 cycles look like recovery
    r = svc.advance(incident, 16)
    session.commit()
    log(f"⑤ 16 cycles observed — outcome={r['outcome']} stable_streak={r['cycles'][-1]['stable_streak']}")

    # ⑥ cycle 17: F27 recurs → reopen → contingency
    r = svc.advance(incident, 1)
    session.commit()
    session.refresh(incident)
    log(f"⑥ cycle 17 — outcome={r['outcome']} → {incident.state.value}")
    assert incident.state == WorkflowState.CONTINGENCY_AWAITING_APPROVAL, incident.state

    # ⑦ supervisor approves contingency (bearing reserved, technician assigned)
    svc.approve_contingency(incident, sup)
    session.commit()
    log(f"⑦ contingency approved — {incident.state.value}")

    # ⑧ technician evidence for bearing replacement, then complete contingency
    c2 = svc._contract(incident)
    svc.submit_evidence(incident, tech, requirement_id=_req_id(session, c2.id, "bearing_post_measurement"),
                        value_num=3.1, unit="mm/s", source="VIB-L4-01 handheld")
    svc.submit_evidence(incident, tech, requirement_id=_req_id(session, c2.id, "technician_completion_2"),
                        value_text="completed")
    svc.complete_contingency(incident)
    session.commit()
    log(f"⑧ contingency complete — second window open — {incident.state.value}")

    # ⑨ 29 stable cycles, then quality release, then the 30th verifies
    svc.advance(incident, 29)
    session.commit()
    svc.submit_evidence(incident, qual, requirement_id=_req_id(session, c2.id, "first_piece_quality"),
                        value_text="pass")
    svc.record_approval(incident, qual, requirement_id=_appr_id(session, c2.id, "quality_release"),
                        reason="first-piece passed; lots dispositioned")
    session.commit()
    r = svc.advance(incident, 1)
    session.commit()
    session.refresh(incident)
    log(f"⑨ 30 stable cycles + quality release — outcome={r['outcome']} → {incident.state.value}")

    kc = session.exec(select(KnowledgeCandidate).where(KnowledgeCandidate.incident_id == incident.id)).first()
    audits = len(session.exec(select(AuditEvent).where(AuditEvent.incident_id == incident.id)).all())
    log(f"✓ {incident.state.value} · reopened {incident.reopened_count}× · audit events {audits} · "
        f"knowledge candidate {kc.status.value if kc else 'none'}")
    return {
        "final_state": incident.state.value,
        "reopened_count": incident.reopened_count,
        "audit_events": audits,
        "knowledge_status": kc.status.value if kc else None,
    }


def run_demo() -> dict:
    with Session(engine) as session:
        return run_scenario(session)
