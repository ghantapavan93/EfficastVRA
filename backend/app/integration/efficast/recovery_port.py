"""EfficastRecoveryPort — the versioned integration boundary (contract v0.1).

A structural ``Protocol`` the three adapters (Synthetic / Replay / Sandbox) implement. Reads return
contract events (``contract.py``); proposals return a ``ProposalResult`` — they are *advisory* requests the
host MES may act on, never direct effects. There are deliberately **no machine-control methods**: this port
can never start/stop a machine, change a setpoint, bypass an interlock, or auto-release quality. Those live
in the frozen ``PROHIBITED_ACTIONS`` set and are absent here by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from app.integration.efficast.contract import (
    AssetContext,
    Intervention,
    LotTrace,
    MachineEvent,
    OperatorObservation,
    PlannerImpact,
    ProductionCycle,
    ProductionOrderContext,
    QualityCheck,
    SensorHealth,
    TelemetryObservation,
    WorkOrder,
)


@dataclass
class ProposalResult:
    """An advisory proposal's outcome. ``accepted`` means the adapter recorded/forwarded it — NOT that the
    host MES executed anything. Proposals never carry side effects of their own."""
    accepted: bool
    kind: str
    ref: str = ""
    note: str = ""
    proposed_at: Optional[datetime] = None
    payload: dict = field(default_factory=dict)


@runtime_checkable
class EfficastRecoveryPort(Protocol):
    # ── reads (return contract v0.1 events) ──────────────────────────────────
    def get_asset_context(self, machine_id: str) -> Optional[AssetContext]: ...
    def get_machine_events(self, machine_id: str, *, limit: int = 50) -> list[MachineEvent]: ...
    def get_telemetry_window(self, machine_id: str, *, since: Optional[datetime] = None,
                             until: Optional[datetime] = None) -> list[TelemetryObservation]: ...
    def get_production_cycles(self, machine_id: str, *, since: Optional[datetime] = None,
                              until: Optional[datetime] = None) -> list[ProductionCycle]: ...
    def get_active_production_order(self, machine_id: str) -> Optional[ProductionOrderContext]: ...
    def get_work_order(self, work_order_id: str) -> Optional[WorkOrder]: ...
    def get_intervention(self, intervention_id: str) -> Optional[Intervention]: ...
    def get_quality_status(self, order_id: str) -> list[QualityCheck]: ...
    def get_affected_lots(self, order_id: str) -> list[LotTrace]: ...
    def get_operator_evidence(self, incident_id: str) -> list[OperatorObservation]: ...
    def get_sensor_health(self, machine_id: str) -> list[SensorHealth]: ...
    def get_planner_impact(self, order_id: str) -> Optional[PlannerImpact]: ...

    # ── proposals (advisory; never direct effects) ───────────────────────────
    def request_evidence(self, incident_id: str, keys: list[str], *, reason: str = "") -> ProposalResult: ...
    def request_approval(self, incident_id: str, requirement_key: str, *, role: str = "") -> ProposalResult: ...
    def propose_incident_reopen(self, incident_id: str, *, reason: str = "") -> ProposalResult: ...
    def publish_recovery_status(self, incident_id: str, decision_type: str, *, summary: str = "") -> ProposalResult: ...
    def attach_qualification_record(self, incident_id: str, record: dict) -> ProposalResult: ...
    def create_recovery_debt_proposal(self, incident_id: str, *, waived: list[str], reason: str = "",
                                      expires_in_minutes: int = 90) -> ProposalResult: ...
