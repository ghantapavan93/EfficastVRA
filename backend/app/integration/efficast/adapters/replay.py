"""ReplayEfficastAdapter — serve a sanitised, enveloped event bundle through the EfficastRecoveryPort.

Reads a bundle (in-memory list or JSONL file), reconciles it once (dedup/order/lateness/…), and answers the
port's read methods from the accepted events. Proposal methods are *recorded* (never forwarded anywhere) and
returned as accepted ProposalResults — replay has no live sink, so it can never cause an external effect.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, TypeVar

from app.domain.base import utcnow
from app.integration.efficast.contract import (
    AssetContext,
    EfficastEvent,
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
    parse_event,
)
from app.integration.efficast.reconciliation import reconcile
from app.integration.efficast.recovery_port import ProposalResult

_T = TypeVar("_T", bound=EfficastEvent)


class ReplayEfficastAdapter:
    """Implements EfficastRecoveryPort over a fixed, reconciled bundle (read-only; proposals are recorded)."""

    def __init__(self, events: list[EfficastEvent]):
        self.reconciliation = reconcile(events)
        self.accepted: list[EfficastEvent] = self.reconciliation.accepted
        self.proposals: list[ProposalResult] = []

    @classmethod
    def from_jsonl(cls, path: str) -> "ReplayEfficastAdapter":
        events: list[EfficastEvent] = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(parse_event(json.loads(line)))
        return cls(events)

    def _of(self, model: type[_T]) -> list[_T]:
        return [e for e in self.accepted if isinstance(e, model)]

    # ── reads ────────────────────────────────────────────────────────────────
    def get_asset_context(self, machine_id: str) -> Optional[AssetContext]:
        return next((e for e in self._of(AssetContext) if e.machine_id == machine_id), None)

    def get_machine_events(self, machine_id: str, *, limit: int = 50) -> list[MachineEvent]:
        return [e for e in self._of(MachineEvent) if e.machine_id == machine_id][:limit]

    def get_telemetry_window(self, machine_id: str, *, since: Optional[datetime] = None,
                             until: Optional[datetime] = None) -> list[TelemetryObservation]:
        return [e for e in self._of(TelemetryObservation)
                if e.machine_id == machine_id
                and (since is None or e.source_timestamp >= since)
                and (until is None or e.source_timestamp <= until)]

    def get_production_cycles(self, machine_id: str, *, since: Optional[datetime] = None,
                             until: Optional[datetime] = None) -> list[ProductionCycle]:
        return [e for e in self._of(ProductionCycle) if e.machine_id == machine_id]

    def get_active_production_order(self, machine_id: str) -> Optional[ProductionOrderContext]:
        return next((e for e in self._of(ProductionOrderContext) if not machine_id or e.machine_id == machine_id), None)

    def get_work_order(self, work_order_id: str) -> Optional[WorkOrder]:
        return next((e for e in self._of(WorkOrder) if e.work_order_id == work_order_id), None)

    def get_intervention(self, intervention_id: str) -> Optional[Intervention]:
        return next((e for e in self._of(Intervention) if e.intervention_id == intervention_id), None)

    def get_quality_status(self, order_id: str) -> list[QualityCheck]:
        return [e for e in self._of(QualityCheck) if not order_id or e.order_id == order_id]

    def get_affected_lots(self, order_id: str) -> list[LotTrace]:
        return [e for e in self._of(LotTrace) if not order_id or e.order_id == order_id]

    def get_operator_evidence(self, incident_id: str) -> list[OperatorObservation]:
        return [e for e in self._of(OperatorObservation) if not incident_id or e.incident_id == incident_id]

    def get_sensor_health(self, machine_id: str) -> list[SensorHealth]:
        return [e for e in self._of(SensorHealth) if not machine_id or e.machine_id == machine_id]

    def get_planner_impact(self, order_id: str) -> Optional[PlannerImpact]:
        return next((e for e in self._of(PlannerImpact) if not order_id or e.order_id == order_id), None)

    # ── proposals (recorded only; replay has no live sink) ───────────────────
    def _record(self, kind: str, ref: str, payload: dict) -> ProposalResult:
        pr = ProposalResult(accepted=True, kind=kind, ref=ref, note="recorded (replay has no live sink)",
                            proposed_at=utcnow(), payload=payload)
        self.proposals.append(pr)
        return pr

    def request_evidence(self, incident_id: str, keys: list[str], *, reason: str = "") -> ProposalResult:
        return self._record("request_evidence", incident_id, {"keys": keys, "reason": reason})

    def request_approval(self, incident_id: str, requirement_key: str, *, role: str = "") -> ProposalResult:
        return self._record("request_approval", incident_id, {"requirement_key": requirement_key, "role": role})

    def propose_incident_reopen(self, incident_id: str, *, reason: str = "") -> ProposalResult:
        return self._record("propose_incident_reopen", incident_id, {"reason": reason})

    def publish_recovery_status(self, incident_id: str, decision_type: str, *, summary: str = "") -> ProposalResult:
        return self._record("publish_recovery_status", incident_id, {"decision_type": decision_type, "summary": summary})

    def attach_qualification_record(self, incident_id: str, record: dict) -> ProposalResult:
        return self._record("attach_qualification_record", incident_id, {"record": record})

    def create_recovery_debt_proposal(self, incident_id: str, *, waived: list[str], reason: str = "",
                                      expires_in_minutes: int = 90) -> ProposalResult:
        return self._record("create_recovery_debt_proposal", incident_id,
                            {"waived": waived, "reason": reason, "expires_in_minutes": expires_in_minutes})
