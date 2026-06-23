"""Deterministic synthetic Efficast adapter.

All synthetic-plant behavior lives behind this port. :class:`ScenarioPhysics` is the synthetic
plant's *behavior model* — the deterministic trajectory that produces the cycle-17 relapse in the
first verification window and 30 stable cycles in the second. In a real deployment this class is
gone entirely and telemetry arrives from Efficast Edge; the rest of the app is unchanged.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.adapters.efficast_port import (
    EfficastPort,
    InventoryStatusDTO,
    LotDTO,
    MachineEvent,
    MachineSnapshot,
    MaiaAlertDTO,
    OEEContext,
    ProductionOrderDTO,
    PublishResult,
    QualityStatusDTO,
    ScheduleImpactDTO,
    WorkerEvidenceDTO,
)
from app.config import get_settings
from app.domain.base import id_factory, utcnow
from app.domain.enums import EvidenceStatus
from app.domain.models import (
    DowntimeEvent,
    EvidenceItem,
    InventoryPart,
    Machine,
    MaiaAlert,
    MaterialLot,
    OutboxEvent,
    ProductionOrder,
    QualityCheck,
    ScrapEvent,
)

_settings = get_settings()


class ScenarioPhysics:
    """Pure, deterministic synthetic-plant trajectory (no randomness, no time dependence)."""

    RELAPSE_CYCLE = 17
    FAULT = "F27"

    def synthesize_cycle(self, window_seq: int, cycle_index: int, baseline: dict) -> dict:
        b_temp = float(baseline.get("temp_c", 63.0))
        b_scrap = float(baseline.get("scrap_pct", 1.6))
        i = cycle_index

        if window_seq == 1:
            if i < self.RELAPSE_CYCLE:
                # Window 1 LOOKS like recovery on the headline metrics (the trap the product catches),
                # but the bearing precursor is quietly rising — the signal the Forecaster reads early.
                return {
                    "vibration": round(3.62 - 0.012 * i, 3),          # 3.6 → 3.43  (≤ 4.0 ✓)
                    "temperature": round(max(b_temp, 84.0 - 0.95 * i), 2),  # declining from 84 ✓
                    "cycle_time": round(12.60 - 0.010 * i, 3),        # ~12.5 → 12.44 (within 5% ✓)
                    "scrap_pct": 1.8,                                  # < 2.0 ✓
                    "fault_code": None,
                    "bearing_precursor": round(min(1.0, 0.20 + 0.06 * i), 3),  # hidden drift 0.26 → ~1.0
                }
            # Cycle 17: the originating fault recurs. Recovery was never real.
            return {
                "vibration": 6.8,
                "temperature": 80.0,
                "cycle_time": 14.0,
                "scrap_pct": 3.6,
                "fault_code": self.FAULT,
                "bearing_precursor": 1.0,
            }

        # Window 2: after bearing replacement — genuinely stable for 30 cycles, precursor flat-low.
        return {
            "vibration": round(3.20 - 0.003 * i, 3),                  # 3.2 → 3.11
            "temperature": round(max(b_temp, 70.0 - 0.25 * i), 2),    # declines toward baseline ✓
            "cycle_time": round(12.30 - 0.003 * i, 3),                # ~12.3 → 12.21
            "scrap_pct": b_scrap,                                      # 1.6 < 2.0 ✓
            "fault_code": None,
            "bearing_precursor": round(max(0.05, 0.12 - 0.001 * i), 3),  # healthy: low & flat
        }


class SyntheticEfficastPort(EfficastPort):
    def __init__(self, session: Session):
        self.session = session
        self.physics = ScenarioPhysics()

    # ── inbound MAIA alerts (front of the loop) ──────────────────────────────
    def get_open_alerts(self) -> list[MaiaAlertDTO]:
        alerts = self.session.exec(
            select(MaiaAlert).where(MaiaAlert.status == "open")
            .order_by(MaiaAlert.detected_at)  # type: ignore[arg-type]
        ).all()
        return [
            MaiaAlertDTO(
                id=a.id, source=a.source, kind=a.kind, machine_id=a.machine_id, order_id=a.order_id,
                fault_code=a.fault_code,
                severity=a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                message=a.message, signals=a.signals or {}, detected_at=a.detected_at, status=a.status,
            )
            for a in alerts
        ]

    def acknowledge_alert(self, alert_id: str, *, incident_id: str) -> None:
        a = self.session.get(MaiaAlert, alert_id)
        if a is not None:
            a.status = "triaged"
            a.resulted_in_incident = incident_id
            self.session.add(a)
            self.session.flush()

    # ── reads ────────────────────────────────────────────────────────────────
    def get_machine_snapshot(self, machine_id: str) -> MachineSnapshot:
        m = self.session.get(Machine, machine_id)
        if m is None:
            raise KeyError(f"machine {machine_id} not found")
        live = m.live or {}
        at = None
        if live.get("at"):
            try:
                at = datetime.fromisoformat(live["at"])
            except ValueError:
                at = None
        freshness = int((utcnow() - at).total_seconds()) if at else int(live.get("freshness_s", 0))
        return MachineSnapshot(
            machine_id=m.id,
            code=m.code,
            name=m.name,
            state=m.state.value if hasattr(m.state, "value") else str(m.state),
            vibration=live.get("vibration", m.baseline.get("vibration_mm_s")),
            temperature=live.get("temperature", m.baseline.get("temp_c")),
            cycle_time=live.get("cycle_time", m.baseline.get("cycle_time_s")),
            scrap_pct=live.get("scrap_pct", m.baseline.get("scrap_pct")),
            fault_code=live.get("fault_code"),
            baseline=m.baseline,
            timestamp=at or m.updated_at,
            freshness_s=max(freshness, 0),
        )

    def get_active_production_order(self, machine_id: str) -> Optional[ProductionOrderDTO]:
        order = self.session.exec(
            select(ProductionOrder)
            .where(ProductionOrder.machine_id == machine_id)
            .where(ProductionOrder.status == "in_progress")
        ).first()
        if order is None:
            return None
        return ProductionOrderDTO(
            id=order.id,
            product=order.product,
            qty_total=order.qty_total,
            qty_done=order.qty_done,
            qty_remaining=order.qty_remaining,
            unit=order.unit,
            status=order.status,
            machine_id=order.machine_id,
            due_at=order.due_at,
        )

    def get_recent_machine_events(self, machine_id: str, limit: int = 20) -> list[MachineEvent]:
        events: list[MachineEvent] = []
        for dt in self.session.exec(
            select(DowntimeEvent).where(DowntimeEvent.machine_id == machine_id)
        ).all():
            events.append(
                MachineEvent(
                    at=dt.started_at,
                    kind="fault" if dt.fault_code else "downtime",
                    fault_code=dt.fault_code,
                    detail=dt.reason,
                )
            )
        for sc in self.session.exec(
            select(ScrapEvent).where(ScrapEvent.machine_id == machine_id)
        ).all():
            events.append(MachineEvent(at=sc.at, kind="scrap", detail=f"{sc.qty} units · {sc.reason}"))
        events.sort(key=lambda e: e.at, reverse=True)
        return events[:limit]

    def get_oee_context(self, machine_id: str) -> OEEContext:
        snap = self.get_machine_snapshot(machine_id)
        baseline_cycle = float(snap.baseline.get("cycle_time_s", 12.2)) or 12.2
        cycle = snap.cycle_time or baseline_cycle
        performance = max(0.0, min(1.0, baseline_cycle / cycle))
        scrap = (snap.scrap_pct or 0.0) / 100.0
        quality = max(0.0, 1.0 - scrap)
        availability = 0.80 if snap.fault_code else 0.93
        oee = round(availability * performance * quality, 4)
        return OEEContext(
            availability=round(availability, 4),
            performance=round(performance, 4),
            quality=round(quality, 4),
            oee=oee,
            timestamp=snap.timestamp,
        )

    def get_quality_status(self, *, machine_id: str, order_id: Optional[str] = None) -> QualityStatusDTO:
        lots_on_hold = 0
        if order_id:
            lots_on_hold = len(
                self.session.exec(
                    select(MaterialLot)
                    .where(MaterialLot.order_id == order_id)
                    .where(MaterialLot.disposition == "HOLD")
                ).all()
            )
        open_checks = len(
            self.session.exec(
                select(QualityCheck)
                .where(QualityCheck.order_id == order_id)
                .where(QualityCheck.result == "pending")
            ).all()
        ) if order_id else 0
        return QualityStatusDTO(
            order_id=order_id,
            machine_id=machine_id,
            on_hold=lots_on_hold > 0 or open_checks > 0,
            lots_on_hold=lots_on_hold,
            open_checks=open_checks,
            last_result="pending" if open_checks else "pass",
        )

    def get_affected_lots(self, order_id: str) -> list[LotDTO]:
        lots = self.session.exec(
            select(MaterialLot).where(MaterialLot.order_id == order_id)
        ).all()
        return [
            LotDTO(
                id=lot.id,
                product=lot.product,
                qty=lot.qty,
                disposition=lot.disposition.value if hasattr(lot.disposition, "value") else str(lot.disposition),
                produced_from=lot.produced_from,
                produced_to=lot.produced_to,
            )
            for lot in lots
        ]

    def get_inventory_status(self, part_number: str) -> Optional[InventoryStatusDTO]:
        part = self.session.exec(
            select(InventoryPart).where(InventoryPart.part_number == part_number)
        ).first()
        if part is None:
            return None
        return InventoryStatusDTO(
            part_number=part.part_number,
            name=part.name,
            on_hand=part.on_hand,
            reserved=part.reserved,
            available=part.available,
            location=part.location,
        )

    def get_worker_evidence(self, incident_id: str) -> list[WorkerEvidenceDTO]:
        items = self.session.exec(
            select(EvidenceItem)
            .where(EvidenceItem.incident_id == incident_id)
            .where(EvidenceItem.source_kind == "human")
        ).all()
        out: list[WorkerEvidenceDTO] = []
        for it in items:
            if it.status in (EvidenceStatus.SUBMITTED, EvidenceStatus.VALIDATED):
                out.append(
                    WorkerEvidenceDTO(
                        key=it.requirement_id,
                        label=it.value_text or it.kind.value,
                        submitted_by=it.submitted_by,
                        role=it.submitted_role.value if hasattr(it.submitted_role, "value") else str(it.submitted_role),
                        value_num=it.value_num,
                        value_text=it.value_text,
                        unit=it.unit,
                        at=it.evidence_timestamp,
                    )
                )
        return out

    def get_schedule_impact(self, order_id: str) -> ScheduleImpactDTO:
        order = self.session.get(ProductionOrder, order_id)
        if order is None:
            raise KeyError(f"order {order_id} not found")
        snap_cycle = 12.2
        if order.machine_id:
            snap = self.get_machine_snapshot(order.machine_id)
            snap_cycle = snap.cycle_time or 12.2
        est_minutes = int((order.qty_remaining * snap_cycle) / 60)
        at_risk = bool(order.due_at and order.due_at < utcnow())
        return ScheduleImpactDTO(
            order_id=order.id,
            qty_remaining=order.qty_remaining,
            est_minutes_lost=est_minutes,
            due_at=order.due_at,
            at_risk=at_risk,
        )

    # ── writes (transactional outbox; no external calls) ───────────────────────
    def publish_agent_event(self, *, topic: str, payload: dict, correlation_id: str) -> PublishResult:
        return self._outbox(topic, payload, correlation_id)

    def publish_recovery_decision(self, *, incident_id: str, decision: dict, correlation_id: str) -> PublishResult:
        payload = {"incident_id": incident_id, **decision}
        return self._outbox("recovery.decision", payload, correlation_id)

    def _outbox(self, topic: str, payload: dict, correlation_id: str) -> PublishResult:
        ref = id_factory("OBX")()
        evt = OutboxEvent(
            id=ref,
            tenant_id=_settings.tenant_id,
            topic=topic,
            payload=payload,
            correlation_id=correlation_id,
            status="pending",
            available_at=utcnow(),
        )
        self.session.add(evt)
        self.session.flush()
        return PublishResult(ok=True, ref=ref, topic=topic)
