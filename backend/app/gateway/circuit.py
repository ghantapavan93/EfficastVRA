"""Per-tool circuit breaker (closed → open → half_open)."""

from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session

from app.config import get_settings
from app.domain.base import utcnow
from app.domain.models import CircuitBreakerState

_settings = get_settings()


def _get(session: Session, tool_name: str) -> CircuitBreakerState:
    cb = session.get(CircuitBreakerState, tool_name)
    if cb is None:
        cb = CircuitBreakerState(id=tool_name, tenant_id=_settings.tenant_id, state="closed")
        session.add(cb)
        session.flush()
    return cb


def allow(session: Session, tool_name: str) -> tuple[bool, str]:
    cb = _get(session, tool_name)
    if cb.state == "open":
        if cb.opened_at and (utcnow() - cb.opened_at) > timedelta(seconds=cb.cooldown_s):
            cb.state = "half_open"
            session.add(cb)
            session.flush()
            return True, "half_open probe"
        return False, "circuit open"
    return True, cb.state


def on_success(session: Session, tool_name: str) -> None:
    cb = _get(session, tool_name)
    cb.state = "closed"
    cb.failures = 0
    cb.opened_at = None
    session.add(cb)
    session.flush()


def on_failure(session: Session, tool_name: str) -> None:
    cb = _get(session, tool_name)
    cb.failures += 1
    if cb.failures >= cb.threshold:
        cb.state = "open"
        cb.opened_at = utcnow()
    session.add(cb)
    session.flush()
