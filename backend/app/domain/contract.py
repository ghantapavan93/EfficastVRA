"""The Recovery Contract schema (structured spec).

This Pydantic model is the *shape* of a contract that the reasoning layer drafts/explains and that
deterministic code evaluates. A JSON snapshot is stored on ``RecoveryContract.spec`` for display and
version-to-version comparison, while normalised ORM rows
(:class:`~app.domain.models.RecoveryCondition` etc.) drive evaluation.

Nothing here decides anything — it only *describes* what successful recovery must look like.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.domain.enums import CompareOp, ConditionKind, EvidenceKind, Role


class ConditionSpec(BaseModel):
    key: str
    kind: ConditionKind
    label: str
    op: CompareOp
    threshold: Optional[float] = None
    unit: str = ""
    baseline: Optional[float] = None
    sensor_tag: Optional[str] = None
    fault_code: Optional[str] = None
    deadline_kind: str = "cycles"          # cycles | minutes | window
    deadline_value: Optional[float] = None
    window_cycles: Optional[int] = None
    policy_ref: str = ""
    rationale: str = ""                     # human-readable "why" (from reasoning)


class EvidenceReqSpec(BaseModel):
    key: str
    kind: EvidenceKind
    label: str
    assigned_role: Role
    reason_required: str = ""
    required_before: str = "monitoring"     # monitoring | closure | quality_release
    freshness_max_s: Optional[int] = None
    blocks_conditions: list[str] = Field(default_factory=list)
    validity_rule: dict = Field(default_factory=dict)


class ApprovalReqSpec(BaseModel):
    key: str
    label: str
    required_role: Role
    required_before: str = "monitoring"     # monitoring | contingency | quality_release | closure
    grants: list[str] = Field(default_factory=list)
    denies: list[str] = Field(default_factory=list)
    policy_ref: str = ""


class VerificationWindowSpec(BaseModel):
    required_stable_cycles: int = 30
    max_duration_min: Optional[int] = None
    cycle_seconds: float = 12.2             # nominal cycle length for time estimates


class ClosurePolicySpec(BaseModel):
    description: str = (
        "All machine, production and quality conditions PASSED for the full verification window, "
        "all required evidence VALIDATED and fresh, all approvals APPROVED."
    )
    require_all_conditions: bool = True
    require_quality_release: bool = True
    require_stable_window: bool = True


class ReopeningPolicySpec(BaseModel):
    description: str = (
        "Any machine condition VIOLATED during the verification window — in particular recurrence "
        "of the originating fault — reopens the incident and voids closure."
    )
    reopen_on_fault_recurrence: bool = True
    reopen_on_any_condition_violation: bool = True


class EscalationPolicySpec(BaseModel):
    description: str = (
        "Escalate to plant supervision if recovery fails twice, if a required approval is rejected, "
        "or if the verification window exceeds its maximum duration."
    )
    escalate_after_failures: int = 2
    escalate_on_approval_rejected: bool = True


class RecoveryContractSpec(BaseModel):
    """Full structured contract (the JSON the UI renders as 'a structured operational agreement')."""

    contract_no: str
    version: int = 1
    incident_id: str
    intervention_id: Optional[str] = None
    objective: str
    policy_version: str = ""
    workflow_version: str = ""
    drafted_by: str = ""

    machine_conditions: list[ConditionSpec] = Field(default_factory=list)
    production_conditions: list[ConditionSpec] = Field(default_factory=list)
    quality_conditions: list[ConditionSpec] = Field(default_factory=list)
    evidence_requirements: list[EvidenceReqSpec] = Field(default_factory=list)
    approval_requirements: list[ApprovalReqSpec] = Field(default_factory=list)

    verification_window: VerificationWindowSpec = Field(default_factory=VerificationWindowSpec)
    closure_policy: ClosurePolicySpec = Field(default_factory=ClosurePolicySpec)
    reopening_policy: ReopeningPolicySpec = Field(default_factory=ReopeningPolicySpec)
    escalation_policy: EscalationPolicySpec = Field(default_factory=EscalationPolicySpec)

    def all_conditions(self) -> list[ConditionSpec]:
        return [*self.machine_conditions, *self.production_conditions, *self.quality_conditions]
