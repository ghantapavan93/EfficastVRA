"""EfficastApiPort — reference skeleton for a REAL, authorized Efficast integration.

THIS IS NOT CONNECTED. It documents, in code, exactly how a production adapter would satisfy the same
``EfficastPort`` interface the application core already depends on — so swapping the synthetic adapter
for a real one requires no change above the port (see docs/REAL_DATA_INTEGRATION.md). Every method
raises ``NotConfigured`` until a real client is injected; nothing here calls a real endpoint, and —
as everywhere in this system — there is deliberately **no** machine-control method.

Mapping (illustrative, to be confirmed against a real, authorized API — currently UNKNOWN):
  • telemetry / Live View        → MQTT topic or REST `/machines/{id}/live`  → MachineSnapshot
  • OEE                          → REST `/oee/{machine}`                      → OEEContext
  • consumption (energy/water)   → REST `/consumption/{machine}`             → ConsumptionDTO
  • production orders            → REST `/orders?machine={id}&status=active`  → ProductionOrderDTO
  • quality / scrap / lots       → REST `/quality`, `/lots?order={id}`        → QualityStatusDTO / LotDTO
  • MAIA / agent alerts          → webhook or MQTT `agents/alerts`            → MaiaAlertDTO
  • inventory                    → REST `/inventory/{part}`                   → InventoryStatusDTO
  • publish agent event/decision → REST POST `/agents/events`                 → PublishResult
Historian back-fill of post-intervention cycles would feed the telemetry seam
(app/services/telemetry.py) rather than this port.
"""

from __future__ import annotations

from typing import Optional, Protocol

from app.adapters.efficast_port import (
    ConsumptionDTO,
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


class NotConfigured(RuntimeError):
    """Raised when the real Efficast client is not wired — this skeleton never calls live endpoints."""


class EfficastClient(Protocol):
    """The minimal HTTP/MQTT client a real adapter would inject. Intentionally tiny."""

    def get(self, path: str, **params) -> dict: ...
    def post(self, path: str, body: dict) -> dict: ...


class EfficastApiPort(EfficastPort):
    """Reference implementation against a real Efficast API. Inject a client to make it live; left
    unconfigured here so it can never accidentally hit a network in the prototype."""

    def __init__(self, client: Optional[EfficastClient] = None, *, base_url: str = ""):
        self._client = client
        self._base_url = base_url

    def _require(self) -> EfficastClient:
        if self._client is None:
            raise NotConfigured(
                "EfficastApiPort has no client. This is a documented skeleton; use SyntheticEfficastPort "
                "for the prototype, or inject an authorized client for a real integration."
            )
        return self._client

    # ── inbound MAIA alerts ────────────────────────────────────────────────────
    def get_open_alerts(self) -> list[MaiaAlertDTO]:
        c = self._require()
        rows = c.get("/agents/alerts", status="open").get("alerts", [])
        return [MaiaAlertDTO(**_map_alert(r)) for r in rows]  # pragma: no cover

    def acknowledge_alert(self, alert_id: str, *, incident_id: str) -> None:
        self._require().post(f"/agents/alerts/{alert_id}/ack", {"incident_id": incident_id})  # pragma: no cover

    # ── reads ──────────────────────────────────────────────────────────────────
    def get_machine_snapshot(self, machine_id: str) -> MachineSnapshot:
        c = self._require()
        return MachineSnapshot(**_map_snapshot(c.get(f"/machines/{machine_id}/live")))  # pragma: no cover

    def get_active_production_order(self, machine_id: str) -> Optional[ProductionOrderDTO]:
        raise NotConfigured("map REST /orders?machine={id}&status=active → ProductionOrderDTO")

    def get_recent_machine_events(self, machine_id: str, limit: int = 20) -> list[MachineEvent]:
        raise NotConfigured("map REST /machines/{id}/events → MachineEvent[]")

    def get_oee_context(self, machine_id: str) -> OEEContext:
        raise NotConfigured("map REST /oee/{machine} → OEEContext")

    def get_consumption_snapshot(self, machine_id: str) -> ConsumptionDTO:
        raise NotConfigured("map REST /consumption/{machine} (energy/water/material) → ConsumptionDTO")

    def get_quality_status(self, *, machine_id: str, order_id: Optional[str] = None) -> QualityStatusDTO:
        raise NotConfigured("map REST /quality → QualityStatusDTO")

    def get_affected_lots(self, order_id: str) -> list[LotDTO]:
        raise NotConfigured("map REST /lots?order={id} → LotDTO[]")

    def get_inventory_status(self, part_number: str) -> Optional[InventoryStatusDTO]:
        raise NotConfigured("map REST /inventory/{part} → InventoryStatusDTO")

    def get_worker_evidence(self, incident_id: str) -> list[WorkerEvidenceDTO]:
        raise NotConfigured("map REST /worker-view/evidence?incident={id} → WorkerEvidenceDTO[]")

    def get_schedule_impact(self, order_id: str) -> ScheduleImpactDTO:
        raise NotConfigured("map planner REST /schedule/impact?order={id} → ScheduleImpactDTO")

    # ── publishes (events/decisions only — never machine control) ───────────────
    def publish_agent_event(self, *, topic: str, payload: dict, correlation_id: str) -> PublishResult:
        raise NotConfigured("POST /agents/events → PublishResult")

    def publish_recovery_decision(self, *, incident_id: str, decision: dict, correlation_id: str) -> PublishResult:
        raise NotConfigured("POST /agents/decisions → PublishResult")


def _map_alert(row: dict) -> dict:  # pragma: no cover  (illustrative field mapping)
    return {
        "id": row.get("id"), "source": row.get("source", "MAIA"), "kind": row.get("type", "anomaly"),
        "machine_id": row.get("machineId"), "order_id": row.get("orderId"), "fault_code": row.get("faultCode"),
        "severity": row.get("severity", "S2"), "message": row.get("message", ""),
        "signals": row.get("signals", {}), "detected_at": row.get("detectedAt"), "status": "open",
    }


def _map_snapshot(row: dict) -> dict:  # pragma: no cover  (illustrative field mapping)
    return {
        "machine_id": row.get("id"), "code": row.get("code", ""), "name": row.get("name", ""),
        "state": row.get("state", "RUNNING"), "vibration": row.get("vibrationRms"),
        "temperature": row.get("tempC"), "cycle_time": row.get("cycleTimeS"),
        "scrap_pct": row.get("scrapPct"), "fault_code": row.get("faultCode"),
        "source": "EfficastApiPort", "freshness_s": row.get("freshnessS", 0),
    }
