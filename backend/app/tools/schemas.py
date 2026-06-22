"""Pydantic input/output models for tools."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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


class PublishDecisionInput(BaseModel):
    incident_id: str
    decision_type: str            # verified_recovery | reopened | escalated | conditional
    summary: str = ""


class ReopenInput(BaseModel):
    incident_id: str


class KnowledgeInput(BaseModel):
    incident_id: str
