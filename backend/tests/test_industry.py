"""Industry-grade gap tests (Phase 13): tamper-evident audit chain, escalation, notifications."""

from __future__ import annotations

from sqlmodel import select

from app.domain.enums import Role, WorkflowState
from app.domain.models import AuditEvent, Incident, Notification
from app.seed.northstar import IDS
from app.workflow.audit import verify_audit_chain
from app.workflow.demo import run_scenario
from tests.helpers import to_monitoring


def _active(session) -> Incident:
    return session.exec(select(Incident).where(Incident.historical == False)).first()  # noqa: E712


def test_audit_chain_verifies_and_detects_tampering(session):
    run_scenario(session, log=lambda *a: None)
    inc = _active(session)

    intact = verify_audit_chain(session, inc.correlation_id)
    assert intact["ok"] is True and intact["count"] > 0

    # Tamper with a committed audit row — the hash chain must detect it.
    events = session.exec(
        select(AuditEvent).where(AuditEvent.correlation_id == inc.correlation_id)
        .order_by(AuditEvent.seq)  # type: ignore[arg-type]
    ).all()
    victim = events[len(events) // 2]
    victim.summary = victim.summary + " (altered)"
    session.add(victim)
    session.flush()

    broken = verify_audit_chain(session, inc.correlation_id)
    assert broken["ok"] is False
    assert broken["broken_at_seq"] == victim.seq


def test_notifications_pushed_to_the_right_roles(session):
    run_scenario(session, log=lambda *a: None)
    notes = session.exec(select(Notification)).all()
    by_kind = {n.kind: n for n in notes}

    # The agent pushed the human tasks instead of making people hunt for them.
    assert "approval_required" in by_kind and by_kind["approval_required"].to_role == Role.SUPERVISOR
    assert "evidence_required" in by_kind and by_kind["evidence_required"].to_role == Role.TECHNICIAN
    assert "reopened" in by_kind and by_kind["reopened"].to_role == Role.SUPERVISOR
    assert "verified" in by_kind and by_kind["verified"].to_role == Role.SUPERVISOR
    assert all(n.status == "unread" for n in notes)


def test_escalation_fires_after_repeated_failures(session):
    svc, inc, _c1 = to_monitoring(session)
    inc.reopened_count = 2          # policy escalates once failures reach the threshold
    session.add(inc)
    session.flush()

    result = svc.advance(inc, 17)   # relapse at cycle 17 → violated → escalate (not reopen)
    session.refresh(inc)
    assert result["outcome"] == "escalated"
    assert inc.state == WorkflowState.ESCALATED

    notes = session.exec(
        select(Notification).where(Notification.kind == "escalated")
    ).all()
    roles = {n.to_role for n in notes}
    assert Role.SUPERVISOR in roles and Role.PLANT_ADMIN in roles
