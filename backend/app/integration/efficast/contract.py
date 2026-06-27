"""Efficast Recovery Data Contract v0.1 — the versioned event envelope + the 14 event models.

This is the keystone of the integration layer: every event a host MES sends (or that we replay from a
sanitised bundle) carries the same **envelope**, so reconciliation, replay, and shadow-mode all speak one
language. Pydantic models are the source of truth; ``export_schemas.py`` emits JSON Schema from them into
``schemas/efficast-recovery-v0.1/``.

Honesty: ``source_system`` + ``data_quality`` make provenance explicit; nothing here implies a live Efficast
connection. ``schema_version``/``mapping_version`` let the contract evolve without silent breakage.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

CONTRACT_VERSION = "0.1"


class DataQuality(str, Enum):
    OK = "OK"
    SUSPECT = "SUSPECT"      # present but questionable (out of plausible range, weak source)
    MISSING = "MISSING"      # a required field/sample was absent in the source
    STALE = "STALE"          # older than its freshness budget at ingestion


class EfficastEvent(BaseModel):
    """The envelope every event carries. Subclasses add a typed payload + an ``event_type`` discriminator."""
    # ── identity & versioning ──
    source_system: str                          # e.g. "efficast" | "synthetic" | "replay"
    schema_version: str = CONTRACT_VERSION
    mapping_version: str = "0.1"                 # how the origin schema was mapped → this contract
    tenant_id: str
    plant_id: str
    source_id: str                              # identity of the sending system instance / device
    # ── correlation & idempotency ──
    correlation_id: str                          # ties an event stream to one incident/decision
    idempotency_key: str                         # unique per logical event (dedup anchor)
    # ── time ──
    source_timestamp: datetime                   # when the event occurred in the origin system
    ingestion_timestamp: datetime                # when WE received it
    timezone: str = "UTC"
    # ── quality ──
    data_quality: DataQuality = DataQuality.OK
    event_type: str = "event"


# ── 14 event types ────────────────────────────────────────────────────────────
class AssetContext(EfficastEvent):
    event_type: Literal["asset_context"] = "asset_context"
    machine_id: str
    machine_model: str = ""
    component: str = ""
    line_id: str = ""
    criticality: str = "normal"                  # low | normal | high | critical


class MachineEvent(EfficastEvent):
    event_type: Literal["machine_event"] = "machine_event"
    machine_id: str
    event_code: str                              # e.g. "F27", "STOP", "STARVED"
    severity: str = "info"
    description: str = ""


class TelemetryObservation(EfficastEvent):
    event_type: Literal["telemetry_observation"] = "telemetry_observation"
    machine_id: str
    metric: str                                  # vibration_rms | temperature | cycle_time | scrap_pct | bearing_precursor
    value: float
    unit: str = ""
    sensor_id: str = ""


class ProductionCycle(EfficastEvent):
    event_type: Literal["production_cycle"] = "production_cycle"
    machine_id: str
    order_id: str = ""
    cycle_index: int = 0
    cycle_time_s: Optional[float] = None
    good_count: int = 0
    scrap_count: int = 0
    fault_code: Optional[str] = None


class ProductionOrderContext(EfficastEvent):
    event_type: Literal["production_order_context"] = "production_order_context"
    order_id: str
    product: str = ""
    machine_id: str = ""
    quantity_total: Optional[int] = None
    quantity_remaining: Optional[int] = None


class WorkOrder(EfficastEvent):
    event_type: Literal["work_order"] = "work_order"
    work_order_id: str
    machine_id: str = ""
    kind: str = ""
    status: str = ""                             # open | in_progress | completed | closed


class Intervention(EfficastEvent):
    event_type: Literal["intervention"] = "intervention"
    intervention_id: str
    work_order_id: str = ""
    kind: str = ""                               # e.g. "coupling_alignment", "bearing_replacement"
    component: str = ""
    status: str = ""                             # proposed | in_progress | completed
    completed_at: Optional[datetime] = None


class OperatorObservation(EfficastEvent):
    event_type: Literal["operator_observation"] = "operator_observation"
    machine_id: str = ""
    incident_id: str = ""
    operator: str = ""
    note: str = ""
    value_num: Optional[float] = None
    unit: str = ""


class QualityCheck(EfficastEvent):
    event_type: Literal["quality_check"] = "quality_check"
    order_id: str = ""
    lot_id: str = ""
    result: str = "pass"                         # pass | fail | pending
    metric: str = ""
    value: Optional[float] = None
    spec: str = ""


class LotTrace(EfficastEvent):
    event_type: Literal["lot_trace"] = "lot_trace"
    lot_id: str
    order_id: str = ""
    produced_from: Optional[datetime] = None
    produced_to: Optional[datetime] = None
    disposition: str = "HOLD"                    # HOLD | RELEASED | QUARANTINE | SCRAPPED


class Approval(EfficastEvent):
    event_type: Literal["approval"] = "approval"
    requirement_key: str
    decided_by: str = ""
    decided_role: str = ""
    decision: str = ""                           # approve | reject
    reason: str = ""


class PlannerImpact(EfficastEvent):
    event_type: Literal["planner_impact"] = "planner_impact"
    order_id: str = ""
    delay_minutes: Optional[float] = None
    downstream_orders: list[str] = Field(default_factory=list)
    note: str = ""


class SensorHealth(EfficastEvent):
    event_type: Literal["sensor_health"] = "sensor_health"
    sensor_id: str
    machine_id: str = ""
    metric: str = ""
    status: str = "unknown"                      # trusted | degraded | untrusted | unknown
    calibration_due: Optional[datetime] = None
    last_sample_at: Optional[datetime] = None


class RecoveryDecisionPublication(EfficastEvent):
    event_type: Literal["recovery_decision_publication"] = "recovery_decision_publication"
    incident_id: str
    decision_type: str                           # verified | conditional | failed | insufficient_evidence | reopened | escalated
    summary: str = ""
    effective_at: Optional[datetime] = None


# ── discriminated union + parsing ─────────────────────────────────────────────
AnyEfficastEvent = Annotated[
    Union[
        AssetContext, MachineEvent, TelemetryObservation, ProductionCycle, ProductionOrderContext,
        WorkOrder, Intervention, OperatorObservation, QualityCheck, LotTrace, Approval, PlannerImpact,
        SensorHealth, RecoveryDecisionPublication,
    ],
    Field(discriminator="event_type"),
]

EVENT_MODELS: dict[str, type[EfficastEvent]] = {
    m.model_fields["event_type"].default: m  # type: ignore[union-attr]
    for m in (AssetContext, MachineEvent, TelemetryObservation, ProductionCycle, ProductionOrderContext,
              WorkOrder, Intervention, OperatorObservation, QualityCheck, LotTrace, Approval, PlannerImpact,
              SensorHealth, RecoveryDecisionPublication)
}


class _EventAdapter(BaseModel):
    event: AnyEfficastEvent


def parse_event(obj: dict) -> EfficastEvent:
    """Parse one raw dict into the correct typed event via the ``event_type`` discriminator."""
    return _EventAdapter.model_validate({"event": obj}).event
