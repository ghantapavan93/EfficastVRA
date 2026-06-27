"""Recovery Debt — the conditional-recovery (concession / deviation permit) lifecycle.

Granted only by an authorised human through the gateway (APPROVAL_REQUIRED); never waives a relapse /
quality / safety; makes the disposition CONDITIONAL (never VERIFIED) while active; SETTLES when the waived
condition verifies, or BREACHES at expiry and auto-escalates — never a silent closure."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlmodel import select

from app.domain.base import utcnow
from app.domain.enums import AuditEventType, RecoveryDebtStatus, Role, WorkflowState
from app.domain.models import AuditEvent
from app.gateway import execute as gateway_execute
from app.gateway.gateway import GatewayError
from app.services.disposition import assess_disposition
from app.services.recovery_debt import active_debt, settle_recovery_debt, sweep_recovery_debt
from tests.helpers import principal, to_monitoring, to_quality_released, to_window2_stable


def _grant(session, inc, principal_, *, waived, reason="temperature not fully stable; run reduced",
           restrictions=None, expires_in_minutes=90):
    return gateway_execute(
        session, tool_name="grant_recovery_debt",
        raw_args={"incident_id": inc.id, "waived_condition_keys": waived, "reason": reason,
                  "restrictions": restrictions or ["line speed <= 70%"],
                  "expires_in_minutes": expires_in_minutes,
                  "monitoring_requirement": "thermal inspection every 20 min",
                  "follow_up": "re-measure drive temperature"},
        principal=principal_, correlation_id=inc.correlation_id, incident_id=inc.id)


def test_grant_makes_disposition_conditional_and_audits(session):
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 5)
    out = _grant(session, inc, principal(session, "s.vega"), waived=["temperature_trend"])
    assert out.ok and out.data["status"] == "ACTIVE"

    d = assess_disposition(session, inc)
    assert d["disposition"] == "CONDITIONAL" and d["can_close"] is False
    assert d["recovery_debt"]["active"] is True and d["recovery_debt"]["restrictions"]

    audits = session.exec(select(AuditEvent).where(AuditEvent.incident_id == inc.id)).all()
    assert any(a.type == AuditEventType.RECOVERY_DEBT_GRANTED for a in audits)


def test_grant_denied_for_unauthorised_role(session):
    svc, inc, _c1 = to_monitoring(session)
    with pytest.raises(GatewayError):  # technician is not an approver — gateway role stage denies
        _grant(session, inc, principal(session, "a.lang"), waived=["temperature_trend"])


def test_grant_denied_for_non_waivable_condition(session):
    svc, inc, _c1 = to_monitoring(session)
    with pytest.raises(GatewayError):  # fault non-recurrence (a relapse) can never be waived — policy denies
        _grant(session, inc, principal(session, "s.vega"), waived=["fault_f27"])


def test_settle_when_waived_condition_verifies(session):
    _svc, inc, _c2 = to_window2_stable(session, cycles=30)   # machine conditions pass at 30 stable cycles
    _grant(session, inc, principal(session, "s.vega"), waived=["vibration_rms"])
    debt = settle_recovery_debt(session, inc, actor="s.vega", role=Role.SUPERVISOR)
    assert debt.status == RecoveryDebtStatus.SETTLED and debt.settled_at is not None


def test_breach_auto_escalates(session):
    svc, inc, _c1 = to_monitoring(session)
    svc.advance(inc, 5)
    _grant(session, inc, principal(session, "s.vega"), waived=["temperature_trend"], expires_in_minutes=1)
    debt = active_debt(session, inc)
    debt.expires_at = utcnow() - timedelta(minutes=5)   # force the waiver past expiry, unsettled
    session.add(debt)
    session.flush()
    swept = sweep_recovery_debt(session, inc)
    assert swept.status == RecoveryDebtStatus.BREACHED
    session.refresh(inc)
    assert inc.state == WorkflowState.ESCALATED            # never a silent closure


def test_active_debt_blocks_verified_even_when_eligible(session):
    _svc, inc, _c2 = to_quality_released(session, cycles=30)   # otherwise VERIFIED-eligible
    assert assess_disposition(session, inc)["disposition"] == "VERIFIED"   # baseline (no debt)
    _grant(session, inc, principal(session, "s.vega"), waived=["vibration_rms"])
    after = assess_disposition(session, inc)
    assert after["disposition"] == "CONDITIONAL" and after["can_close"] is False
