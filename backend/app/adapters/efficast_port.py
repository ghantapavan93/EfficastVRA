"""Abstract Efficast adapter port + the DTOs that cross it.

A real, authorized implementation (``EfficastApiPort``) would implement the same interface against
Efficast's private API. The application core depends only on this contract.

NOTE: there is deliberately **no** method that controls a machine (start/stop/restart/PLC/set-point/
alarm/interlock/LOTO). The port reads evidence and publishes events/decisions — nothing more.
"""

from __future__ import annotations

import abc
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── DTOs ─────────────────────────────────────────────────────────────────────
class MachineSnapshot(BaseModel):
    machine_id: str
    code: str
    name: str
    state: str
    vibration: Optional[float] = None       # mm/s RMS
    temperature: Optional[float] = None     # °C
    cycle_time: Optional[float] = None      # s
    scrap_pct: Optional[float] = None
    fault_code: Optional[str] = None
    baseline: dict = Field(default_factory=dict)
    timestamp: Optional[datetime] = None
    source: str = "SyntheticEfficastPort"
    freshness_s: int = 0


class ProductionOrderDTO(BaseModel):
    id: str
    product: str
    qty_total: int
    qty_done: int
    qty_remaining: int
    unit: str
    status: str
    machine_id: Optional[str] = None
    due_at: Optional[datetime] = None
    source: str = "SyntheticEfficastPort"


class MachineEvent(BaseModel):
    at: datetime
    kind: str                                # downtime | scrap | fault | quality | stop
    fault_code: Optional[str] = None
    detail: str = ""
    source: str = "SyntheticEfficastPort"


class OEEContext(BaseModel):
    availability: float
    performance: float
    quality: float
    oee: float
    timestamp: Optional[datetime] = None
    source: str = "SyntheticEfficastPort"


class QualityStatusDTO(BaseModel):
    order_id: Optional[str] = None
    machine_id: Optional[str] = None
    on_hold: bool = True
    lots_on_hold: int = 0
    open_checks: int = 0
    last_result: str = "pending"
    source: str = "SyntheticEfficastPort"


class LotDTO(BaseModel):
    id: str
    product: str
    qty: int
    disposition: str
    produced_from: Optional[datetime] = None
    produced_to: Optional[datetime] = None
    source: str = "SyntheticEfficastPort"


class InventoryStatusDTO(BaseModel):
    part_number: str
    name: str
    on_hand: int
    reserved: int
    available: int
    location: str = ""
    source: str = "SyntheticEfficastPort"


class WorkerEvidenceDTO(BaseModel):
    key: str
    label: str
    submitted_by: str
    role: str
    value_num: Optional[float] = None
    value_text: str = ""
    unit: str = ""
    at: Optional[datetime] = None
    source: str = "SyntheticEfficastPort"


class ScheduleImpactDTO(BaseModel):
    order_id: str
    qty_remaining: int
    est_minutes_lost: int
    due_at: Optional[datetime] = None
    at_risk: bool = False
    source: str = "SyntheticEfficastPort"


class MaiaAlertDTO(BaseModel):
    id: str
    source: str = "MAIA"
    kind: str = "fault_recurrence"
    machine_id: str
    order_id: Optional[str] = None
    fault_code: Optional[str] = None
    severity: str = "S2"
    message: str = ""
    signals: dict = Field(default_factory=dict)
    detected_at: Optional[datetime] = None
    status: str = "open"


class PublishResult(BaseModel):
    ok: bool
    ref: str
    topic: str


# ── Port ─────────────────────────────────────────────────────────────────────
class EfficastPort(abc.ABC):
    """Read evidence from / publish events to the host MES. No machine control."""

    @abc.abstractmethod
    def get_open_alerts(self) -> list[MaiaAlertDTO]:
        """Inbound MAIA/agent alerts awaiting triage. The agent reads these — it never raises machine
        control from them."""
        ...

    @abc.abstractmethod
    def acknowledge_alert(self, alert_id: str, *, incident_id: str) -> None:
        """Mark a MAIA alert as triaged once it has produced an incident."""
        ...

    @abc.abstractmethod
    def get_machine_snapshot(self, machine_id: str) -> MachineSnapshot: ...

    @abc.abstractmethod
    def get_active_production_order(self, machine_id: str) -> Optional[ProductionOrderDTO]: ...

    @abc.abstractmethod
    def get_recent_machine_events(self, machine_id: str, limit: int = 20) -> list[MachineEvent]: ...

    @abc.abstractmethod
    def get_oee_context(self, machine_id: str) -> OEEContext: ...

    @abc.abstractmethod
    def get_quality_status(self, *, machine_id: str, order_id: Optional[str] = None) -> QualityStatusDTO: ...

    @abc.abstractmethod
    def get_affected_lots(self, order_id: str) -> list[LotDTO]: ...

    @abc.abstractmethod
    def get_inventory_status(self, part_number: str) -> Optional[InventoryStatusDTO]: ...

    @abc.abstractmethod
    def get_worker_evidence(self, incident_id: str) -> list[WorkerEvidenceDTO]: ...

    @abc.abstractmethod
    def get_schedule_impact(self, order_id: str) -> ScheduleImpactDTO: ...

    @abc.abstractmethod
    def publish_agent_event(self, *, topic: str, payload: dict, correlation_id: str) -> PublishResult: ...

    @abc.abstractmethod
    def publish_recovery_decision(self, *, incident_id: str, decision: dict, correlation_id: str) -> PublishResult: ...
