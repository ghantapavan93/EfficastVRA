# Real-data integration

The prototype runs on a deterministic synthetic plant, but the architecture is built so that **real
data replaces the synthetic source without touching the application core**. There are exactly two
seams, both already present.

## Seam 1 — the host MES (`EfficastPort`)
The application core depends only on the abstract `EfficastPort` (`app/adapters/efficast_port.py`).
- Prototype: `SyntheticEfficastPort` (deterministic seed data).
- Production: `EfficastApiPort` (`app/adapters/efficast_api.py`) — a documented, **not-connected**
  skeleton showing the field-by-field mapping from a real Efficast REST/MQTT/OPC-UA surface to the
  port DTOs. Inject an authorized client and it goes live; nothing above the port changes.

The port reads evidence and publishes events/decisions. It has **no machine-control method** — start/
stop/restart/PLC/setpoint/alarm/interlock/LOTO are not expressible through it, by design.

## Seam 2 — post-intervention telemetry (`TelemetrySource`)
Recovery is judged cycle-by-cycle from telemetry. The cycle engine pulls each sample from a
`TelemetrySource` (`app/services/telemetry.py`):
- `SyntheticTelemetrySource` — the demo plant (`ScenarioPhysics`).
- `IngestedTelemetrySource` — real readings, consumed FIFO.

`resolve_source` prefers real ingested telemetry for a machine when present, else falls back to
synthetic — so a real feed "just works":

```bash
# Push real readings for a machine; the next verification cycles consume them.
curl -X POST localhost:8000/api/telemetry/MCH-L4-CONV \
  -H 'X-VRA-User: s.vega' -H 'Content-Type: application/json' \
  -d '{"readings":[{"vibration":3.5,"temperature":70,"cycle_time":12.3,"scrap_pct":1.5}]}'
```

The **same deterministic evaluator** then verifies recovery on the real data — proven by
`tests/test_telemetry.py` (ingested samples become the recorded observations). A production deployment
would stream from Efficast Edge / a historian into this endpoint (or a queue) instead of curl.

## Any machine, any signal
The evaluator speaks generic `CompareOp` over arbitrary metric keys, and machine classes are declared
as data (`MachineProfile`, see [`MACHINE_AGNOSTIC.md`](MACHINE_AGNOSTIC.md)). So a real integration is:
1. add/confirm the `MachineProfile` for the equipment class,
2. point `EfficastApiPort` at the authorized API,
3. stream telemetry to the ingestion seam.

No business logic, evaluator, gateway, or workflow code changes. That is what makes this *compatible
with real data and the machinery a host MES connects* — while staying an independent, synthetic-data
prototype today (no official Efficast integration is claimed).

## Production hardening (when real)
Postgres + pgvector (already the Docker path), an idempotent ingestion queue (the transactional
outbox pattern is in place), per-tenant API auth, and backpressure on the telemetry endpoint. See
[`PRODUCTION_EVOLUTION.md`](PRODUCTION_EVOLUTION.md).
