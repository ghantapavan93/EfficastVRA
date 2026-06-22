"""Durable incident state machine.

Pure-Python transition table + guards. Every transition validates current state, the legality of
the target, the actor's role, and (optionally) an optimistic-lock version, then appends a
``STATE_TRANSITION`` audit row. The interface is intentionally Temporal-shaped: a single
``transition()`` entry point that a future Temporal activity could wrap unchanged.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from app.domain.enums import AuditEventType, Role, WorkflowState
from app.domain.models import Incident
from app.workflow.audit import record_audit

S = WorkflowState

# ── Legal transitions ────────────────────────────────────────────────────────
ALLOWED: dict[WorkflowState, set[WorkflowState]] = {
    # front of the loop (MAIA alert → agent triage → human accepts the proposed intervention)
    S.ALERT_TRIAGED: {S.INTERVENTION_PROPOSED, S.CANCELLED},
    S.INTERVENTION_PROPOSED: {S.INTERVENTION_RECORDED, S.CANCELLED},
    S.INTERVENTION_RECORDED: {S.RECOVERY_CONTRACT_DRAFTED, S.CANCELLED},
    S.RECOVERY_CONTRACT_DRAFTED: {S.RECOVERY_CONTRACT_REVIEWED, S.CANCELLED},
    S.RECOVERY_CONTRACT_REVIEWED: {S.AWAITING_REQUIRED_EVIDENCE, S.CANCELLED},
    S.AWAITING_REQUIRED_EVIDENCE: {S.READY_FOR_MONITORING, S.INSUFFICIENT_EVIDENCE, S.CANCELLED},
    S.READY_FOR_MONITORING: {S.MONITORING_RECOVERY, S.CANCELLED},
    S.MONITORING_RECOVERY: {
        S.MONITORING_RECOVERY,            # self-loop: each observed cycle
        S.RECOVERY_CONDITION_PENDING,
        S.RECOVERY_CONDITION_FAILED,
        S.VERIFIED_RECOVERY,
        S.INSUFFICIENT_EVIDENCE,
        S.ESCALATED,
    },
    S.RECOVERY_CONDITION_PENDING: {
        S.MONITORING_RECOVERY,
        S.RECOVERY_CONDITION_FAILED,
        S.VERIFIED_RECOVERY,
        S.ESCALATED,
    },
    S.RECOVERY_CONDITION_FAILED: {S.RECOVERY_FAILED, S.INCIDENT_REOPENED, S.ESCALATED},
    S.INSUFFICIENT_EVIDENCE: {S.AWAITING_REQUIRED_EVIDENCE, S.MONITORING_RECOVERY, S.ESCALATED},
    S.RECOVERY_FAILED: {S.INCIDENT_REOPENED, S.ESCALATED},
    S.INCIDENT_REOPENED: {S.CONTINGENCY_AWAITING_APPROVAL, S.ESCALATED, S.CANCELLED},
    S.CONTINGENCY_AWAITING_APPROVAL: {S.CONTINGENCY_IN_PROGRESS, S.ESCALATED, S.CANCELLED},
    S.CONTINGENCY_IN_PROGRESS: {
        S.AWAITING_REQUIRED_EVIDENCE,
        S.READY_FOR_MONITORING,
        S.ESCALATED,
        S.CANCELLED,
    },
    S.VERIFIED_RECOVERY: set(),   # terminal
    S.ESCALATED: set(),           # terminal
    S.CANCELLED: set(),           # terminal
}

# ── Role guards ──────────────────────────────────────────────────────────────
# (from, to) -> allowed roles. (None, to) is a wildcard on the source state.
# If a transition is not listed, any authorised role may perform it (the Agent Action Gateway
# already authorised the *action* that triggered it; this is defence in depth).
_ANY_AUTOMATIC = {Role.SYSTEM, Role.AGENT}
TRANSITION_GUARD: dict[tuple[Optional[WorkflowState], WorkflowState], set[Role]] = {
    # the agent triages + proposes; a human (supervisor) accepts the diagnosis to record the intervention
    (S.ALERT_TRIAGED, S.INTERVENTION_PROPOSED): _ANY_AUTOMATIC,
    (S.INTERVENTION_PROPOSED, S.INTERVENTION_RECORDED): {Role.SUPERVISOR, Role.PLANT_ADMIN},
    (S.RECOVERY_CONTRACT_DRAFTED, S.RECOVERY_CONTRACT_REVIEWED): {Role.SUPERVISOR, Role.PLANT_ADMIN},
    (S.CONTINGENCY_AWAITING_APPROVAL, S.CONTINGENCY_IN_PROGRESS): {Role.SUPERVISOR, Role.PLANT_ADMIN},
    (S.RECOVERY_CONDITION_FAILED, S.RECOVERY_FAILED): _ANY_AUTOMATIC,
    (S.RECOVERY_FAILED, S.INCIDENT_REOPENED): _ANY_AUTOMATIC,
    (S.INCIDENT_REOPENED, S.CONTINGENCY_AWAITING_APPROVAL): _ANY_AUTOMATIC,
    (None, S.VERIFIED_RECOVERY): _ANY_AUTOMATIC,  # only the orchestrator, after policy + quality release
    (None, S.CANCELLED): {Role.SUPERVISOR, Role.PLANT_ADMIN},
    (None, S.ESCALATED): {Role.SYSTEM, Role.AGENT, Role.SUPERVISOR, Role.PLANT_ADMIN},
}


class StateError(Exception):
    """Illegal transition, bad role, or version conflict."""

    def __init__(self, message: str, *, code: str = "illegal_transition"):
        super().__init__(message)
        self.code = code


def is_legal(from_state: WorkflowState, to_state: WorkflowState) -> bool:
    return to_state in ALLOWED.get(from_state, set())


def _role_allowed(from_state: WorkflowState, to_state: WorkflowState, role: Role) -> bool:
    if (from_state, to_state) in TRANSITION_GUARD:
        return role in TRANSITION_GUARD[(from_state, to_state)]
    if (None, to_state) in TRANSITION_GUARD:
        return role in TRANSITION_GUARD[(None, to_state)]
    return True


def transition(
    session: Session,
    incident: Incident,
    to_state: WorkflowState,
    *,
    actor: str,
    role: Role,
    reason: str,
    expected_version: Optional[int] = None,
    detail: Optional[dict] = None,
) -> Incident:
    """Validate + apply a state transition, appending an audit row. Raises :class:`StateError`."""
    from_state = incident.state

    # Optimistic lock
    if expected_version is not None and incident.version != expected_version:
        raise StateError(
            f"version conflict: expected {expected_version}, found {incident.version}",
            code="version_conflict",
        )

    # Legality (self-loop on MONITORING_RECOVERY is allowed and idempotent-friendly)
    if not is_legal(from_state, to_state):
        raise StateError(
            f"illegal transition {from_state.value} → {to_state.value}",
            code="illegal_transition",
        )

    # Role guard
    if not _role_allowed(from_state, to_state, role):
        raise StateError(
            f"role {role.value} may not perform {from_state.value} → {to_state.value}",
            code="role_denied",
        )

    incident.state = to_state
    incident.version += 1
    session.add(incident)
    session.flush()

    record_audit(
        session,
        type=AuditEventType.STATE_TRANSITION,
        correlation_id=incident.correlation_id,
        actor=actor,
        role=role,
        summary=f"{from_state.value} → {to_state.value}: {reason}",
        plant_id=incident.plant_id,
        incident_id=incident.id,
        contract_id=incident.current_contract_id,
        detail=detail or {},
        prev_state=from_state,
        new_state=to_state,
    )
    return incident
