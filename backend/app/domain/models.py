"""All ORM models (SQLModel tables).

Organisation mirrors the three separated systems:
  A. Manufacturing Evidence   B. Durable Operational Workflow   C. Agent / Safety / Audit

Conventions
-----------
* Every row has ``created_at`` / ``updated_at`` / ``version`` (from :class:`Base`).
* Operational rows carry ``tenant_id`` + ``plant_id`` for scoping, and ``correlation_id`` to tie a
  whole recovery thread together in the audit trail.
* Foreign keys are plain string columns (no ORM relationships) — explicit queries only, which keeps
  sessions predictable and avoids lazy-load surprises.
* JSON columns use ``sa_type=JSON`` (maps to JSONB-style storage on Postgres, JSON on SQLite).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, UniqueConstraint
from sqlmodel import Field

from app.domain.base import Base, id_factory, utcnow
from app.domain.enums import (
    ActionClass,
    ApprovalStatus,
    AuditEventType,
    CompareOp,
    ConditionKind,
    ConditionStatus,
    DocApprovalStatus,
    DocumentType,
    EvidenceKind,
    EvidenceStatus,
    InterventionStatus,
    KnowledgeStatus,
    LotDisposition,
    MachineState,
    RecoveryDebtStatus,
    OutcomeType,
    Role,
    Severity,
    ToolStatus,
    WorkflowState,
)

# ─────────────────────────────────────────────────────────────────────────────
# Identity (local auth principal)
# ─────────────────────────────────────────────────────────────────────────────


class User(Base, table=True):
    id: str = Field(default_factory=id_factory("USR"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    username: str = Field(index=True, unique=True)
    display_name: str
    role: Role = Field(index=True)
    active: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# System A — Manufacturing Evidence
# ─────────────────────────────────────────────────────────────────────────────


class Plant(Base, table=True):
    id: str = Field(default_factory=id_factory("PLANT"), primary_key=True)
    tenant_id: str = Field(index=True)
    code: str = Field(index=True)
    name: str
    timezone: str = "UTC"


class ProductionLine(Base, table=True):
    id: str = Field(default_factory=id_factory("LINE"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(foreign_key="plant.id", index=True)
    code: str = Field(index=True)
    name: str


class Machine(Base, table=True):
    id: str = Field(default_factory=id_factory("MCH"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(foreign_key="plant.id", index=True)
    line_id: Optional[str] = Field(default=None, foreign_key="productionline.id", index=True)
    code: str = Field(index=True)
    name: str
    machine_model: str = ""
    manufacturer: str = ""
    state: MachineState = MachineState.RUNNING
    # baseline metrics used by recovery conditions (vibration_mm_s, temp_c, cycle_time_s, scrap_pct)
    baseline: dict = Field(default_factory=dict, sa_type=JSON)
    # latest cached sensor readings (updated by the monitoring service each cycle)
    live: dict = Field(default_factory=dict, sa_type=JSON)


class Component(Base, table=True):
    id: str = Field(default_factory=id_factory("CMP"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    machine_id: str = Field(foreign_key="machine.id", index=True)
    name: str
    kind: str = ""  # motor | coupling | bearing | drive | ...
    part_number: str = ""
    installed_at: Optional[datetime] = None
    health_note: str = ""


class Sensor(Base, table=True):
    id: str = Field(default_factory=id_factory("SNS"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    machine_id: str = Field(foreign_key="machine.id", index=True)
    component_id: Optional[str] = Field(default=None, foreign_key="component.id")
    tag: str = Field(index=True)  # e.g. VIB-L4-01
    kind: str = ""  # vibration | temperature | cycle_time
    unit: str = ""


class ProductionOrder(Base, table=True):
    id: str = Field(default_factory=id_factory("PO"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    line_id: Optional[str] = Field(default=None, foreign_key="productionline.id")
    machine_id: Optional[str] = Field(default=None, foreign_key="machine.id", index=True)
    product: str = ""
    qty_total: int = 0
    qty_done: int = 0
    unit: str = "units"
    status: str = "in_progress"
    due_at: Optional[datetime] = None

    @property
    def qty_remaining(self) -> int:
        return max(self.qty_total - self.qty_done, 0)


class Operator(Base, table=True):
    id: str = Field(default_factory=id_factory("OPR"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    name: str
    shift_code: str = ""


class Shift(Base, table=True):
    id: str = Field(default_factory=id_factory("SHF"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    code: str
    name: str
    start_hour: int = 6
    end_hour: int = 14


class DowntimeEvent(Base, table=True):
    id: str = Field(default_factory=id_factory("DT"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    machine_id: str = Field(foreign_key="machine.id", index=True)
    order_id: Optional[str] = Field(default=None, foreign_key="productionorder.id")
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_s: int = 0
    reason: str = ""
    fault_code: Optional[str] = Field(default=None, index=True)  # e.g. F27


class ScrapEvent(Base, table=True):
    id: str = Field(default_factory=id_factory("SCR"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    machine_id: str = Field(foreign_key="machine.id", index=True)
    order_id: Optional[str] = Field(default=None, foreign_key="productionorder.id")
    qty: int = 0
    reason: str = ""
    at: datetime


class QualityCheck(Base, table=True):
    id: str = Field(default_factory=id_factory("QC"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    machine_id: Optional[str] = Field(default=None, foreign_key="machine.id")
    order_id: Optional[str] = Field(default=None, foreign_key="productionorder.id")
    lot_id: Optional[str] = Field(default=None, foreign_key="materiallot.id")
    kind: str = "first_piece"  # first_piece | audit | release
    result: str = "pending"  # pending | pass | fail
    inspector: str = ""
    spec_ref: str = ""
    at: Optional[datetime] = None


class MaterialLot(Base, table=True):
    id: str = Field(default_factory=id_factory("LOT"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    order_id: Optional[str] = Field(default=None, foreign_key="productionorder.id", index=True)
    machine_id: Optional[str] = Field(default=None, foreign_key="machine.id")
    product: str = ""
    qty: int = 0
    disposition: LotDisposition = LotDisposition.HOLD
    produced_from: Optional[datetime] = None
    produced_to: Optional[datetime] = None


class InventoryPart(Base, table=True):
    id: str = Field(default_factory=id_factory("INV"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    part_number: str = Field(index=True)  # e.g. BR-6205
    name: str = ""
    on_hand: int = 0
    reserved: int = 0
    location: str = ""

    @property
    def available(self) -> int:
        return max(self.on_hand - self.reserved, 0)


class Technician(Base, table=True):
    id: str = Field(default_factory=id_factory("TECH"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    name: str
    skills: list = Field(default_factory=list, sa_type=JSON)


class WorkOrder(Base, table=True):
    id: str = Field(default_factory=id_factory("WO"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    machine_id: str = Field(foreign_key="machine.id", index=True)
    kind: str = "corrective"  # corrective | preventive
    title: str = ""
    status: str = "open"  # open | in_progress | completed | closed
    technician_id: Optional[str] = Field(default=None, foreign_key="technician.id")
    opened_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Intervention(Base, table=True):
    """A proposed/completed maintenance action whose recovery we verify.

    ``status == COMPLETED`` means a technician finished the work — it is explicitly **not** proof of
    recovery. That distinction is the entire product.
    """

    id: str = Field(default_factory=id_factory("ITV"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    incident_id: Optional[str] = Field(default=None, foreign_key="incident.id", index=True)
    work_order_id: Optional[str] = Field(default=None, foreign_key="workorder.id")
    machine_id: str = Field(foreign_key="machine.id", index=True)
    component_id: Optional[str] = Field(default=None, foreign_key="component.id")
    sequence: int = 1  # 1 = alignment correction, 2 = bearing replacement (contingency)
    kind: str = ""  # coupling_alignment | bearing_replacement
    title: str = ""
    description: str = ""
    hypothesis: str = ""
    status: InterventionStatus = InterventionStatus.PROPOSED
    technician_id: Optional[str] = Field(default=None, foreign_key="technician.id")
    proposed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    measurements: dict = Field(default_factory=dict, sa_type=JSON)


class Document(Base, table=True):
    """A manual / procedure / spec / policy / incident report / technician note (RAG corpus)."""

    id: str = Field(default_factory=id_factory("DOC"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_scope: str = Field(index=True)  # plant id or "ALL"
    doc_type: DocumentType = Field(index=True)
    title: str = ""
    manufacturer: str = ""
    machine_model: str = ""  # applicability
    component: str = ""
    revision: str = ""
    effective_date: Optional[datetime] = None
    approval_status: DocApprovalStatus = Field(default=DocApprovalStatus.APPROVED, index=True)
    superseded_by: Optional[str] = Field(default=None)  # document id


class DocumentChunk(Base, table=True):
    """A retrievable chunk with full provenance metadata + a stored embedding vector (JSON)."""

    id: str = Field(default_factory=id_factory("CHK"), primary_key=True)
    tenant_id: str = Field(index=True)
    document_id: str = Field(foreign_key="document.id", index=True)
    plant_scope: str = Field(index=True)
    doc_type: DocumentType = Field(index=True)
    manufacturer: str = ""
    machine_model: str = ""
    component: str = ""
    revision: str = ""
    effective_date: Optional[datetime] = None
    approval_status: DocApprovalStatus = Field(default=DocApprovalStatus.APPROVED, index=True)
    superseded_by: Optional[str] = None
    page: int = 0
    section: str = ""
    content: str = ""
    content_hash: str = Field(default="", index=True)
    embedding: list = Field(default_factory=list, sa_type=JSON)


# ─────────────────────────────────────────────────────────────────────────────
# System B — Durable Operational Workflow / Recovery
# ─────────────────────────────────────────────────────────────────────────────


class MaiaAlert(Base, table=True):
    """An inbound alert from a host-MES agent (Efficast's MAIA / specialised agents).

    This is the *trigger* at the front of the loop: MAIA detects/alerts; the Verified Recovery Agent
    triages it, proposes an intervention, and (after a human accepts) verifies the recovery. The agent
    never controls a machine — it reads this alert and reasons. ``signals`` carries the degradation
    snapshot MAIA observed (trend, fault recurrences, scrap rise).
    """

    id: str = Field(default_factory=id_factory("ALERT"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    source: str = "MAIA"                       # which host agent raised it
    kind: str = "fault_recurrence"             # fault_recurrence | bottleneck | anomaly | quality_drift
    machine_id: str = Field(foreign_key="machine.id", index=True)
    order_id: Optional[str] = Field(default=None, foreign_key="productionorder.id")
    fault_code: Optional[str] = None
    severity: Severity = Severity.S2
    message: str = ""
    signals: dict = Field(default_factory=dict, sa_type=JSON)
    detected_at: Optional[datetime] = None
    status: str = Field(default="open", index=True)   # open | triaged | dismissed
    resulted_in_incident: Optional[str] = None
    correlation_id: str = ""


class Incident(Base, table=True):
    id: str = Field(default_factory=id_factory("INC"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    machine_id: str = Field(foreign_key="machine.id", index=True)
    order_id: Optional[str] = Field(default=None, foreign_key="productionorder.id")
    correlation_id: str = Field(index=True)
    dedupe_key: str = Field(index=True, unique=True)  # idempotent incident creation
    source_event_id: Optional[str] = None
    title: str = ""
    severity: Severity = Severity.S2
    state: WorkflowState = Field(default=WorkflowState.INTERVENTION_RECORDED, index=True)
    current_contract_id: Optional[str] = Field(default=None)
    reopened_count: int = 0
    fault_code: Optional[str] = Field(default=None, index=True)
    origin_alert_id: Optional[str] = Field(default=None, index=True)  # MAIA alert that triggered triage
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    # historical incidents power the "compare past interventions" tool
    historical: bool = Field(default=False, index=True)
    outcome_type: Optional[OutcomeType] = None
    outcome_summary: str = ""
    # When a mission is created from an uploaded plant export, the intake analysis (mapping + readiness +
    # reconstruction + provenance) is stored here so the mission carries its own origin story. Empty for
    # alert-originated incidents.
    intake: dict = Field(default_factory=dict, sa_type=JSON)


class MappingProfile(Base, table=True):
    """A reusable Plant Data Mapping Profile — how an uploaded export's columns map onto the Efficast
    Recovery Data Contract. Persisted per plant so the next upload reuses it (operational, not one-time)."""

    id: str = Field(default_factory=id_factory("MAP"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    name: str = ""
    profile_version: str = "1.0"           # NOT Base.version (optimistic-lock int) — this is the mapping rev
    source_filename: str = ""
    mappings: list = Field(default_factory=list, sa_type=JSON)


class RecoveryContract(Base, table=True):
    """The product's core primitive. Drafted/explained by reasoning; evaluated by deterministic code.

    Normalised child rows (conditions / evidence reqs / approval reqs) drive evaluation; ``spec`` is
    a JSON snapshot of the full structured contract for display + version comparison.
    """

    id: str = Field(default_factory=id_factory("RC"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    incident_id: str = Field(foreign_key="incident.id", index=True)
    intervention_id: Optional[str] = Field(default=None, foreign_key="intervention.id")
    contract_no: str = Field(index=True)  # stable human number e.g. RC-1042
    version: int = 1
    status: str = Field(default="draft", index=True)  # draft|reviewed|active|violated|superseded|fulfilled
    policy_version: str = ""
    workflow_version: str = ""
    objective: str = ""
    drafted_by: str = ""  # reasoning provider id
    superseded_by: Optional[str] = None
    verification_window: dict = Field(default_factory=dict, sa_type=JSON)
    closure_policy: dict = Field(default_factory=dict, sa_type=JSON)
    reopening_policy: dict = Field(default_factory=dict, sa_type=JSON)
    escalation_policy: dict = Field(default_factory=dict, sa_type=JSON)
    spec: dict = Field(default_factory=dict, sa_type=JSON)  # full RecoveryContractSpec snapshot


class RecoveryCondition(Base, table=True):
    id: str = Field(default_factory=id_factory("COND"), primary_key=True)
    tenant_id: str = Field(index=True)
    contract_id: str = Field(foreign_key="recoverycontract.id", index=True)
    incident_id: str = Field(index=True)
    kind: ConditionKind
    key: str  # vibration_rms | temperature_trend | fault_f27 | cycle_time | scrap | first_piece | stable_cycles
    label: str = ""
    op: CompareOp
    threshold: Optional[float] = None
    unit: str = ""
    baseline: Optional[float] = None
    sensor_tag: Optional[str] = None
    fault_code: Optional[str] = None
    deadline_kind: str = "cycles"  # cycles | minutes | window
    deadline_value: Optional[float] = None
    window_cycles: Optional[int] = None  # for stable-cycle / not-recur windows
    status: ConditionStatus = ConditionStatus.NOT_EVALUATED
    current_value: Optional[float] = None
    evaluated_at: Optional[datetime] = None
    policy_ref: str = ""
    detail: dict = Field(default_factory=dict, sa_type=JSON)


class EvidenceRequirement(Base, table=True):
    id: str = Field(default_factory=id_factory("EVR"), primary_key=True)
    tenant_id: str = Field(index=True)
    contract_id: str = Field(foreign_key="recoverycontract.id", index=True)
    incident_id: str = Field(index=True)
    condition_id: Optional[str] = Field(default=None, foreign_key="recoverycondition.id")
    kind: EvidenceKind
    key: str
    label: str = ""
    assigned_role: Role
    reason_required: str = ""
    required_before: str = "monitoring"  # monitoring | closure | quality_release
    freshness_max_s: Optional[int] = None
    due_at: Optional[datetime] = None
    status: EvidenceStatus = EvidenceStatus.MISSING
    blocks_conditions: list = Field(default_factory=list, sa_type=JSON)  # condition keys
    validity_rule: dict = Field(default_factory=dict, sa_type=JSON)


class EvidenceItem(Base, table=True):
    id: str = Field(default_factory=id_factory("EVI"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    requirement_id: str = Field(foreign_key="evidencerequirement.id", index=True)
    contract_id: str = Field(index=True)
    incident_id: str = Field(index=True)
    kind: EvidenceKind
    submitted_by: str = ""
    submitted_role: Role = Role.SYSTEM
    value_num: Optional[float] = None
    value_text: str = ""
    unit: str = ""
    source: str = ""  # sensor tag / person / document id
    source_kind: str = "human"  # sensor | human | document | system
    evidence_timestamp: Optional[datetime] = None
    received_at: datetime = Field(default_factory=utcnow)
    freshness_s: Optional[int] = None
    valid: bool = False
    status: EvidenceStatus = EvidenceStatus.SUBMITTED
    conflict_reason: str = ""
    file_ref: Optional[str] = None


class ApprovalRequirement(Base, table=True):
    id: str = Field(default_factory=id_factory("APR"), primary_key=True)
    tenant_id: str = Field(index=True)
    contract_id: str = Field(foreign_key="recoverycontract.id", index=True)
    incident_id: str = Field(index=True)
    key: str  # release_contingency | quality_release | begin_second_window | reserve_bearing ...
    label: str = ""
    required_role: Role
    required_before: str = "monitoring"  # monitoring | contingency | quality_release | closure
    grants: list = Field(default_factory=list, sa_type=JSON)  # what approving authorises
    denies: list = Field(default_factory=list, sa_type=JSON)  # what it explicitly does NOT authorise
    status: ApprovalStatus = ApprovalStatus.PENDING
    policy_ref: str = ""


class ApprovalDecision(Base, table=True):
    id: str = Field(default_factory=id_factory("APD"), primary_key=True)
    tenant_id: str = Field(index=True)
    requirement_id: str = Field(foreign_key="approvalrequirement.id", index=True)
    contract_id: str = Field(index=True)
    incident_id: str = Field(index=True)
    decided_by: str = ""
    decided_role: Role = Role.SYSTEM
    decision: str = "approve"  # approve | reject
    reason: str = ""
    policy_ref: str = ""
    idempotency_key: str = Field(index=True)
    decided_at: datetime = Field(default_factory=utcnow)


class RecoveryWindow(Base, table=True):
    id: str = Field(default_factory=id_factory("WIN"), primary_key=True)
    tenant_id: str = Field(index=True)
    incident_id: str = Field(foreign_key="incident.id", index=True)
    contract_id: str = Field(index=True)
    sequence: int = 1
    required_stable_cycles: int = 30
    observed_cycles: int = 0
    stable_streak: int = 0
    status: str = "open"  # open | monitoring | passed | failed
    baseline: dict = Field(default_factory=dict, sa_type=JSON)
    # Operating context for the Comparable-Conditions Gate: the *normal* reference vs the conditions during
    # this verification window (product/speed/load/lot/mode/shift/ambient/sensor health). If before≠after
    # the apparent recovery may be a confound — see services/comparable_conditions.py. PROTOTYPE_ASSUMPTION.
    baseline_context: dict = Field(default_factory=dict, sa_type=JSON)
    observed_context: dict = Field(default_factory=dict, sa_type=JSON)
    opened_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class RecoveryObservation(Base, table=True):
    id: str = Field(default_factory=id_factory("OBS"), primary_key=True)
    tenant_id: str = Field(index=True)
    incident_id: str = Field(foreign_key="incident.id", index=True)
    contract_id: str = Field(index=True)
    window_id: str = Field(foreign_key="recoverywindow.id", index=True)
    cycle_index: int = 0
    at: datetime
    vibration: Optional[float] = None
    temperature: Optional[float] = None
    cycle_time: Optional[float] = None
    scrap_pct: Optional[float] = None
    fault_code: Optional[str] = None
    # A hidden degradation precursor (e.g. drive-end bearing high-frequency vibration / crest factor).
    # The headline metrics can look recovered while this rises — the Recovery Forecaster reads it.
    bearing_precursor: Optional[float] = None
    source: str = "SyntheticEfficastPort"
    freshness_s: int = 0
    raw: dict = Field(default_factory=dict, sa_type=JSON)


class RecoveryDebt(Base, table=True):
    """A time-boxed *conditional recovery* — a concession / deviation permit. Production may continue under
    explicit restrictions while a specific (waivable) recovery condition is not yet met. It is tracked so a
    CONDITIONAL recovery can never silently become a permanent closure: it must be SETTLED (the waived
    condition later verifies) or it BREACHES at expiry and auto-escalates. Granted only by an authorised
    human through the Agent Action Gateway (APPROVAL_REQUIRED). It can never waive a relapse (fault
    non-recurrence), a quality condition, or anything safety-bearing — see services/recovery_debt.py."""

    id: str = Field(default_factory=id_factory("DEBT"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    incident_id: str = Field(foreign_key="incident.id", index=True)
    contract_id: str = Field(index=True)
    status: RecoveryDebtStatus = Field(default=RecoveryDebtStatus.ACTIVE, index=True)
    waived_condition_keys: list = Field(default_factory=list, sa_type=JSON)
    reason: str = ""
    restrictions: list = Field(default_factory=list, sa_type=JSON)   # e.g. ["line speed <= 70%"]
    monitoring_requirement: str = ""                                 # e.g. "thermal inspection every 20 min"
    follow_up: str = ""
    granted_by: str = ""
    granted_role: Optional[Role] = None
    granted_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    settled_at: Optional[datetime] = None
    settled_by: str = ""
    resolution_note: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# System C — Agent / Safety / Audit / Reliability
# ─────────────────────────────────────────────────────────────────────────────


class ActionProposal(Base, table=True):
    id: str = Field(default_factory=id_factory("ACT"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    incident_id: Optional[str] = Field(default=None, index=True)
    correlation_id: str = Field(index=True)
    proposed_by: str = "agent"
    tool_name: str = Field(index=True)
    action_class: Optional[ActionClass] = None
    args: dict = Field(default_factory=dict, sa_type=JSON)
    idempotency_key: str = Field(index=True)
    status: str = "proposed"  # proposed | approved | denied | executed | failed
    risk_reason: str = ""


class ToolExecution(Base, table=True):
    id: str = Field(default_factory=id_factory("TEX"), primary_key=True)
    tenant_id: str = Field(index=True)
    proposal_id: Optional[str] = Field(default=None, foreign_key="actionproposal.id")
    incident_id: Optional[str] = Field(default=None, index=True)
    correlation_id: str = Field(index=True)
    tool_name: str = Field(index=True)
    actor: str = ""
    role: Role = Role.AGENT
    status: ToolStatus = ToolStatus.SUCCESS
    input_data: dict = Field(default_factory=dict, sa_type=JSON)
    output_data: dict = Field(default_factory=dict, sa_type=JSON)
    error_type: Optional[str] = None
    data_source: Optional[str] = None
    data_timestamp: Optional[datetime] = None
    freshness_s: Optional[int] = None
    idempotency_key: Optional[str] = Field(default=None, index=True)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class AuditEvent(Base, table=True):
    # The per-correlation sequence must be unique — so a concurrent writer (real on Postgres) fails loudly
    # on a seq collision rather than silently forking the tamper-evident hash chain. (H8 hardening.)
    __table_args__ = (UniqueConstraint("correlation_id", "seq", name="uq_audit_correlation_seq"),)

    id: str = Field(default_factory=id_factory("AUD"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    correlation_id: str = Field(index=True)
    incident_id: Optional[str] = Field(default=None, index=True)
    contract_id: Optional[str] = None
    seq: int = Field(default=0, index=True)  # monotonic per correlation thread
    type: AuditEventType = Field(index=True)
    actor: str = ""
    role: Role = Role.SYSTEM
    summary: str = ""
    detail: dict = Field(default_factory=dict, sa_type=JSON)
    prev_state: Optional[WorkflowState] = None
    new_state: Optional[WorkflowState] = None
    policy_version: str = ""
    workflow_version: str = ""
    model_version: str = ""
    prompt_version: str = ""
    # Tamper-evidence: each entry hashes the previous one, forming a per-correlation hash chain.
    prev_hash: str = ""
    entry_hash: str = Field(default="", index=True)
    # Keyed signature over entry_hash (HMAC-SHA256). Empty when no signing key is configured. Makes the
    # chain *unforgeable* without the secret — a DB-level attacker cannot recompute it like the public hash.
    entry_hmac: str = ""


class Notification(Base, table=True):
    """A task/alert pushed to a person or role — so personnel don't have to hunt for what to do next.

    In the prototype the channel is in-app (read at /api/notifications); a real deployment swaps the
    dispatch sink for Efficast's WhatsApp/email (see app/services/notifications.py).
    """

    id: str = Field(default_factory=id_factory("NOTI"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    incident_id: Optional[str] = Field(default=None, index=True)
    correlation_id: str = ""
    to_role: Role = Field(index=True)
    to_user: Optional[str] = None
    channel: str = "in_app"            # in_app | whatsapp | email (synthetic)
    kind: str = ""                      # evidence_required | approval_required | reopened | verified | escalated | diagnosis_proposed
    title: str = ""
    body: str = ""
    status: str = Field(default="unread", index=True)   # unread | read
    action_path: str = ""               # deep-link the UI can route to


class KnowledgeCandidate(Base, table=True):
    id: str = Field(default_factory=id_factory("KNW"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    incident_id: str = Field(foreign_key="incident.id", index=True)
    title: str = ""
    lesson: str = ""
    component: str = ""
    applicable_models: list = Field(default_factory=list, sa_type=JSON)
    conditions: dict = Field(default_factory=dict, sa_type=JSON)
    supporting_evidence: list = Field(default_factory=list, sa_type=JSON)
    failed_intervention: str = ""
    successful_intervention: str = ""
    status: KnowledgeStatus = KnowledgeStatus.PENDING_REVIEW
    reviewer_role: Role = Role.QUALITY_ENGINEER
    review_due: Optional[datetime] = None
    reviewed_by: Optional[str] = None        # who curated it into institutional knowledge
    reviewed_at: Optional[datetime] = None
    review_reason: str = ""


class AgentReasoningTrace(Base, table=True):
    """A single node in the bounded agent reasoning graph (perceive→…→reflect).

    Makes the agent's reasoning inspectable and auditable. The agent *proposes* via these steps; the
    deterministic evaluator + gateway remain the authority (see docs/AGENT_RESEARCH.md).
    """

    id: str = Field(default_factory=id_factory("RSN"), primary_key=True)
    tenant_id: str = Field(index=True)
    plant_id: str = Field(index=True)
    incident_id: str = Field(foreign_key="incident.id", index=True)
    contract_id: Optional[str] = None
    correlation_id: str = Field(index=True)
    seq: int = Field(default=0, index=True)  # monotonic per incident
    node: str = Field(index=True)            # perceive|retrieve|hypothesize|draft|self_critique|verify|decide|reflect|observe
    title: str = ""
    rationale: str = ""
    inputs: dict = Field(default_factory=dict, sa_type=JSON)
    outputs: dict = Field(default_factory=dict, sa_type=JSON)
    citations: list = Field(default_factory=list, sa_type=JSON)
    confidence: Optional[float] = None       # 0..1 calibrated
    revision: int = 0                         # reflexion iteration index
    model_version: str = ""
    prompt_version: str = ""


class TelemetrySample(Base, table=True):
    """A real telemetry reading ingested from a host MES / historian (Efficast Edge), awaiting
    consumption by a verification window.

    In synthetic mode the cycle engine generates samples from ``ScenarioPhysics``; when real samples
    are present for a machine they take precedence (see app/services/telemetry.py). This is the seam
    that lets the same evaluator run on real plant data without any other change.
    """

    id: str = Field(default_factory=id_factory("TLM"), primary_key=True)
    tenant_id: str = Field(index=True)
    machine_id: str = Field(index=True)
    seq: int = Field(default=0, index=True)
    vibration: Optional[float] = None
    temperature: Optional[float] = None
    cycle_time: Optional[float] = None
    scrap_pct: Optional[float] = None
    fault_code: Optional[str] = None
    extra: dict = Field(default_factory=dict, sa_type=JSON)   # additional machine-class signals
    source: str = "ingested"
    consumed: bool = Field(default=False, index=True)
    received_at: Optional[datetime] = None


class OutboxEvent(Base, table=True):
    """Transactional outbox: events written in the same tx as state changes, published reliably."""

    id: str = Field(default_factory=id_factory("OBX"), primary_key=True)
    tenant_id: str = Field(index=True)
    topic: str = Field(index=True)
    payload: dict = Field(default_factory=dict, sa_type=JSON)
    correlation_id: str = Field(index=True)
    status: str = Field(default="pending", index=True)  # pending | published | failed
    attempts: int = 0
    available_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    last_error: str = ""


class IdempotencyRecord(Base, table=True):
    """Dedupe ledger for write actions. Key uniqueness guarantees once-only effects."""

    id: str = Field(primary_key=True)  # the idempotency key itself
    tenant_id: str = Field(index=True)
    scope: str = Field(index=True)
    result_ref: str = ""
    detail: dict = Field(default_factory=dict, sa_type=JSON)


class CircuitBreakerState(Base, table=True):
    """Per-tool circuit breaker (closed → open → half_open)."""

    id: str = Field(primary_key=True)  # tool name
    tenant_id: str = Field(index=True)
    state: str = "closed"  # closed | open | half_open
    failures: int = 0
    threshold: int = 3
    opened_at: Optional[datetime] = None
    cooldown_s: int = 30
