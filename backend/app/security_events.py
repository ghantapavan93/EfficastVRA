"""First-class security-event taxonomy + an in-process registry (the SIEM-ready detection stream).

Every gateway denial, rate-limit throttle, oversized-payload rejection, and prohibited-action attempt
is emitted here. Each event is (a) written as a structured JSON log line — the seam a real deployment
ships to a SIEM — and (b) kept in a bounded ring buffer so the live ``/api/security`` posture can show
recent security activity and per-kind counts.

This layer is pure **detection**: it has no authority to change state and performs no side effects on the
domain. It mirrors the in-memory metrics registry in ``app.observability`` (per-process, best-effort).
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Optional

from app.domain.base import utcnow

log = logging.getLogger("vra.security")

# Map a gateway denial *stage* → (event kind, severity). Severity ladder: info < warning < critical.
_STAGE_KIND: dict[str, tuple[str, str]] = {
    "risk_class": ("prohibited_action_attempt", "critical"),
    "identity": ("unauthenticated_attempt", "warning"),
    "plant_scope": ("cross_tenant_attempt", "critical"),
    "role": ("insufficient_role", "warning"),
    "policy": ("policy_violation", "warning"),
    "human_approval": ("non_human_approval_attempt", "critical"),
    "circuit_breaker": ("circuit_open", "warning"),
    "rate_limit": ("rate_limit_exceeded", "warning"),
    "schema": ("malformed_request", "info"),
}
SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}


@dataclass
class SecurityEvent:
    kind: str
    severity: str
    actor: str = "unknown"
    role: Optional[str] = None
    route: str = ""
    tool: str = ""
    stage: str = ""
    reason: str = ""
    source_ip: str = ""
    correlation_id: str = ""
    at: str = ""


class _Registry:
    """Bounded, thread-safe ring buffer of recent security events + per-kind counters."""

    def __init__(self, maxlen: int = 256) -> None:
        self._lock = Lock()
        self._recent: deque[SecurityEvent] = deque(maxlen=maxlen)
        self._counts: dict[str, int] = {}

    def emit(self, ev: SecurityEvent) -> SecurityEvent:
        ev.at = ev.at or utcnow().isoformat()
        with self._lock:
            self._recent.append(ev)
            self._counts[ev.kind] = self._counts.get(ev.kind, 0) + 1
        log.warning(
            "security_event kind=%s severity=%s actor=%s role=%s stage=%s tool=%s route=%s "
            "source_ip=%s correlation_id=%s reason=%s",
            ev.kind, ev.severity, ev.actor, ev.role, ev.stage, ev.tool, ev.route,
            ev.source_ip, ev.correlation_id, ev.reason,
        )
        return ev

    def counts(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)

    def total(self) -> int:
        with self._lock:
            return sum(self._counts.values())

    def critical_count(self) -> int:
        with self._lock:
            return sum(1 for e in self._recent if e.severity == "critical")

    def recent(self, n: int = 20) -> list[dict]:
        with self._lock:
            return [asdict(e) for e in list(self._recent)[-n:]][::-1]  # newest first

    def reset(self) -> None:
        """Test hook — clears the buffer + counters."""
        with self._lock:
            self._recent.clear()
            self._counts.clear()


REGISTRY = _Registry()


def emit(kind: str, severity: str, **fields) -> SecurityEvent:
    """Emit an ad-hoc security event (e.g. oversized request, rate-limit hit at the HTTP edge)."""
    return REGISTRY.emit(SecurityEvent(kind=kind, severity=severity, **fields))


def emit_denial(
    *,
    stage: str,
    tool: str = "",
    reason: str = "",
    principal=None,
    correlation_id: str = "",
    route: str = "",
    source_ip: str = "",
) -> SecurityEvent:
    """Emit a structured security event for a gateway denial, classified by pipeline *stage*."""
    kind, severity = _STAGE_KIND.get(stage, ("action_denied", "warning"))
    role = getattr(getattr(principal, "role", None), "value", None) if principal else None
    actor = getattr(principal, "username", "unknown") if principal else "unknown"
    return REGISTRY.emit(SecurityEvent(
        kind=kind, severity=severity, actor=actor, role=role, route=route, tool=tool,
        stage=stage, reason=reason, source_ip=source_ip, correlation_id=correlation_id,
    ))
