# Efficast Recovery Data Contract — v0.1

*The versioned event contract Verified Recovery consumes. Pydantic models in
`backend/app/integration/efficast/contract.py` are the source of truth; JSON Schema is generated from them
into `schemas/efficast-recovery-v0.1/` (run `python -m app.integration.efficast.export_schemas`).*

## The envelope (every event carries it)
| Field | Purpose |
|---|---|
| `source_system` | who emitted it — `efficast` \| `synthetic` \| `replay` (provenance, never spoofed) |
| `schema_version` | contract version (this doc = `0.1`) |
| `mapping_version` | how the origin schema was mapped → this contract (lets mapping evolve safely) |
| `tenant_id`, `plant_id` | scope (multi-tenant / multi-plant isolation) |
| `source_id` | the sending device/system instance identity |
| `correlation_id` | ties an event stream to one incident / decision |
| `idempotency_key` | unique per logical event — the **dedup anchor** (covers replayed webhooks) |
| `source_timestamp` | when it happened in the origin system (drives ordering/lateness) |
| `ingestion_timestamp` | when **we** received it (drives clock-drift detection) |
| `timezone` | IANA tz of the source |
| `data_quality` | `OK` \| `SUSPECT` \| `MISSING` \| `STALE` — honest per-event quality |

## The 14 event types
`asset_context` · `machine_event` · `telemetry_observation` · `production_cycle` ·
`production_order_context` · `work_order` · `intervention` · `operator_observation` · `quality_check` ·
`lot_trace` · `approval` · `planner_impact` · `sensor_health` · `recovery_decision_publication`

Each is the envelope + a small typed payload; each carries a `Literal` `event_type` discriminator so a raw
JSONL stream parses unambiguously (`contract.parse_event`). See the per-event JSON Schema files for fields.

## Reconciliation contract (what we do with a messy stream)
`reconciliation.reconcile()` turns a raw stream into `(accepted, anomalies)`:
- **duplicate** — same `idempotency_key` → dropped, recorded (replayed-webhook / lost-response safe).
- **out_of_order / late** — `source_timestamp` < running watermark → flagged; output re-sorted by source time.
- **clock_drift** — `|ingestion − source|` beyond tolerance → flagged.
- **unit_mismatch** — telemetry unit ≠ the metric's canonical unit → flagged.
- **mapping_version_change** — `mapping_version` changes for a source mid-stream → flagged.
- **partial_data** — `data_quality ≠ OK` → flagged.
- **missing_mapping** — unknown/unmappable `event_type` → recorded, never silently accepted.

Nothing is dropped silently — every drop/anomaly keeps its `idempotency_key`.

## Versioning policy
`schema_version` + `mapping_version` are explicit on every event. Additive fields = same version; breaking
changes = a new `efficast-recovery-vX.Y/` schema directory and a new contract module. Consumers must treat
unknown `event_type`s as `missing_mapping`, not errors.

## Honesty
All sample data is **synthetic** (`fixtures.make_f27_bundle`). `source_system` + `data_quality` make
provenance explicit at runtime. This contract describes what we'd accept *from* Efficast — it does not imply
Efficast emits it today (see `EFFICAST_OPEN_QUESTIONS.md`).
