"""Pydantic input/output models for tools."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ToolOutput(BaseModel):
    ok: bool = True
    data: dict = Field(default_factory=dict)
    source: str = ""
    data_timestamp: Optional[datetime] = None
    freshness_s: Optional[int] = None
    ref: Optional[str] = None  # write result reference (idempotency)


# ── read inputs ──────────────────────────────────────────────────────────────
class InterventionInput(BaseModel):
    intervention_id: str


class MachineInput(BaseModel):
    machine_id: str


class OrderInput(BaseModel):
    order_id: str


class QualityInput(BaseModel):
    machine_id: str
    order_id: Optional[str] = None


class IncidentInput(BaseModel):
    incident_id: str


class SearchRequirementsInput(BaseModel):
    query: str
    machine_model: Optional[str] = None
    component: Optional[str] = None


# ── write inputs ─────────────────────────────────────────────────────────────
class RequestEvidenceInput(BaseModel):
    contract_id: str
    requirement_keys: Optional[list[str]] = None  # None => all currently-missing


class SubmitEvidenceInput(BaseModel):
    requirement_id: str
    value_num: Optional[float] = None
    value_text: str = ""
    unit: str = ""
    source: str = ""
    evidence_timestamp: Optional[datetime] = None
    file_ref: Optional[str] = None


class RecordApprovalInput(BaseModel):
    requirement_id: str
    decision: str = "approve"  # approve | reject
    reason: str = ""

    @field_validator("decision")
    @classmethod
    def _decision_is_explicit(cls, v: str) -> str:
        # Anything other than the two valid values used to be silently coerced to REJECT, burning the
        # one-shot human decision. Reject the ambiguous input loudly instead (gateway → 422).
        if v not in ("approve", "reject"):
            raise ValueError("decision must be exactly 'approve' or 'reject'")
        return v


class PublishDecisionInput(BaseModel):
    incident_id: str
    decision_type: str            # verified_recovery | reopened | escalated | conditional
    summary: str = ""


class ReopenInput(BaseModel):
    incident_id: str


class KnowledgeInput(BaseModel):
    incident_id: str


class GrantRecoveryDebtInput(BaseModel):
    """Grant a time-boxed conditional-recovery waiver. APPROVAL_REQUIRED — an authorised human only."""
    incident_id: str
    waived_condition_keys: list[str]          # the (waivable) recovery condition(s) being deferred
    reason: str
    restrictions: list[str] = Field(default_factory=list)   # operating limits for the conditional period
    expires_in_minutes: int = 90              # the waiver is valid only for this long
    monitoring_requirement: str = ""          # extra monitoring while operating on debt
    follow_up: str = ""                       # the action that must close the debt

    @field_validator("waived_condition_keys")
    @classmethod
    def _at_least_one(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("a recovery debt must waive at least one condition")
        return v

    @field_validator("expires_in_minutes")
    @classmethod
    def _bounded_expiry(cls, v: int) -> int:
        # a waiver is a SHORT exception, never indefinite — bound it (1 minute … 24 hours)
        if not (1 <= v <= 24 * 60):
            raise ValueError("expires_in_minutes must be between 1 and 1440 (24h)")
        return v
