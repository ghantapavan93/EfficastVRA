"""Shared enumerations — the vocabulary of the whole system.

All enums subclass ``str`` so they serialize transparently to JSON and store as TEXT in SQLite /
VARCHAR in Postgres.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    SUPERVISOR = "supervisor"
    TECHNICIAN = "technician"
    QUALITY_ENGINEER = "quality_engineer"
    PLANT_ADMIN = "plant_admin"
    # Non-human principals (cannot satisfy human-approval requirements):
    AGENT = "agent"
    SYSTEM = "system"


class WorkflowState(str, Enum):
    """The durable incident / recovery lifecycle (see docs/STATE_MACHINE.md)."""

    # ── front of the loop: MAIA alert → agent triage → proposed intervention ──
    ALERT_TRIAGED = "ALERT_TRIAGED"
    INTERVENTION_PROPOSED = "INTERVENTION_PROPOSED"

    INTERVENTION_RECORDED = "INTERVENTION_RECORDED"
    RECOVERY_CONTRACT_DRAFTED = "RECOVERY_CONTRACT_DRAFTED"
    RECOVERY_CONTRACT_REVIEWED = "RECOVERY_CONTRACT_REVIEWED"
    AWAITING_REQUIRED_EVIDENCE = "AWAITING_REQUIRED_EVIDENCE"
    READY_FOR_MONITORING = "READY_FOR_MONITORING"
    MONITORING_RECOVERY = "MONITORING_RECOVERY"
    RECOVERY_CONDITION_PENDING = "RECOVERY_CONDITION_PENDING"
    RECOVERY_CONDITION_FAILED = "RECOVERY_CONDITION_FAILED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    INCIDENT_REOPENED = "INCIDENT_REOPENED"
    CONTINGENCY_AWAITING_APPROVAL = "CONTINGENCY_AWAITING_APPROVAL"
    CONTINGENCY_IN_PROGRESS = "CONTINGENCY_IN_PROGRESS"
    VERIFIED_RECOVERY = "VERIFIED_RECOVERY"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


# States in which the incident is finished and no further automatic progression occurs.
TERMINAL_STATES: frozenset[WorkflowState] = frozenset(
    {WorkflowState.VERIFIED_RECOVERY, WorkflowState.ESCALATED, WorkflowState.CANCELLED}
)


class ActionClass(str, Enum):
    """Risk classification assigned by the Agent Action Gateway."""

    READ_ONLY = "READ_ONLY"
    REVERSIBLE_AUTOMATIC = "REVERSIBLE_AUTOMATIC"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    PROHIBITED = "PROHIBITED"


class Severity(str, Enum):
    S1 = "S1"  # critical
    S2 = "S2"  # high
    S3 = "S3"  # medium
    S4 = "S4"  # low


class EvidenceStatus(str, Enum):
    MISSING = "MISSING"
    REQUESTED = "REQUESTED"
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    CONFLICTING = "CONFLICTING"
    EXPIRED = "EXPIRED"


class EvidenceKind(str, Enum):
    NUMERIC_MEASUREMENT = "NUMERIC_MEASUREMENT"
    TEXT_OBSERVATION = "TEXT_OBSERVATION"
    PHOTO = "PHOTO"
    FILE = "FILE"
    APPROVAL = "APPROVAL"
    COMPLETION = "COMPLETION"  # technician marks intervention work complete


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ConditionKind(str, Enum):
    MACHINE = "MACHINE"
    PRODUCTION = "PRODUCTION"
    QUALITY = "QUALITY"


class ConditionStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    BLOCKED = "BLOCKED"  # cannot evaluate (missing/stale evidence)
    PENDING = "PENDING"  # evaluating, deadline not reached
    PASSING = "PASSING"  # currently meeting target (not yet final)
    PASSED = "PASSED"  # satisfied for the required duration/window
    VIOLATED = "VIOLATED"


class CompareOp(str, Enum):
    """How a condition's observed value is compared to its threshold."""

    LTE = "<="
    GTE = ">="
    LT = "<"
    GT = ">"
    EQ = "=="
    WITHIN_PCT = "within_pct"      # |value - baseline| / baseline <= threshold
    DECLINING = "declining"        # trend over window is negative
    NOT_RECUR = "not_recur"        # fault code must not reappear
    COUNT_GTE = "count_gte"        # e.g. >= N stable cycles


class DocumentType(str, Enum):
    MANUAL = "MANUAL"
    PROCEDURE = "PROCEDURE"
    QUALITY_SPEC = "QUALITY_SPEC"
    RECOVERY_POLICY = "RECOVERY_POLICY"
    INCIDENT_REPORT = "INCIDENT_REPORT"
    TECH_NOTE = "TECH_NOTE"


class DocApprovalStatus(str, Enum):
    APPROVED = "APPROVED"
    OBSOLETE = "OBSOLETE"
    DRAFT = "DRAFT"
    UNAPPROVED = "UNAPPROVED"


class OutcomeType(str, Enum):
    VERIFIED = "VERIFIED"
    CONDITIONAL = "CONDITIONAL"
    FAILED = "FAILED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    ESCALATED = "ESCALATED"


class ToolStatus(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    DENIED = "DENIED"


class KnowledgeStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class InterventionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"          # technician completion — NOT proof of recovery
    SUPERSEDED = "SUPERSEDED"


class MachineState(str, Enum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    STOPPED = "STOPPED"
    ALERT = "ALERT"


class LotDisposition(str, Enum):
    HOLD = "HOLD"
    RELEASED = "RELEASED"
    QUARANTINE = "QUARANTINE"
    SCRAPPED = "SCRAPPED"


class AuditEventType(str, Enum):
    STATE_TRANSITION = "STATE_TRANSITION"
    ACTION_PROPOSED = "ACTION_PROPOSED"
    ALERT_INGESTED = "ALERT_INGESTED"
    DIAGNOSIS_PROPOSED = "DIAGNOSIS_PROPOSED"
    DIAGNOSIS_ACCEPTED = "DIAGNOSIS_ACCEPTED"
    ACTION_CLASSIFIED = "ACTION_CLASSIFIED"
    ACTION_DENIED = "ACTION_DENIED"
    TOOL_EXECUTED = "TOOL_EXECUTED"
    EVIDENCE_REQUESTED = "EVIDENCE_REQUESTED"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    EVIDENCE_VALIDATED = "EVIDENCE_VALIDATED"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED"
    APPROVAL_RECORDED = "APPROVAL_RECORDED"
    CONTRACT_DRAFTED = "CONTRACT_DRAFTED"
    CONTRACT_VIOLATED = "CONTRACT_VIOLATED"
    INCIDENT_REOPENED = "INCIDENT_REOPENED"
    RECOVERY_VERIFIED = "RECOVERY_VERIFIED"
    KNOWLEDGE_CANDIDATE_CREATED = "KNOWLEDGE_CANDIDATE_CREATED"
    REASONING_INVOKED = "REASONING_INVOKED"
    REASONING_FALLBACK = "REASONING_FALLBACK"
    CIRCUIT_OPENED = "CIRCUIT_OPENED"
    OUTBOX_PUBLISHED = "OUTBOX_PUBLISHED"
    DECISION_PUBLISHED = "DECISION_PUBLISHED"
