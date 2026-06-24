# Integration spec — how the Verified Recovery Agent plugs into a host MES (Efficast‑shaped)

A hand‑over‑ready description of the **read‑only** data contract this verification layer consumes, and the
single thing it publishes back (its verdict). It is written from *our* side: it is the interface **we**
require, expressed against real, tested code ([`app/adapters/efficast_port.py`](../backend/app/adapters/efficast_port.py)).
It is **not** a claim about Efficast's real API — auth, transport, and exact paths are marked *to be agreed
with the host*. See [`EFFICAST_FIT.md`](EFFICAST_FIT.md) for the positioning and the claim‑confidence table.

## The closed loop (who does what)
```
Host MES (Efficast)                         Verified Recovery Agent (this system)
─────────────────────                       ─────────────────────────────────────
detect fault / predict  ──(alert)──▶        triage alert → propose intervention (human accepts)
MAIA closes work order                       draft Recovery Contract (deterministic)
stream telemetry        ──(read)───▶         monitor cycle‑by‑cycle (deterministic evaluator)
                                             cycle 17 relapse → AUTO‑REOPEN + escalate
                                             30 stable + quality release → VERIFIED
verdict to WhatsApp /   ◀──(publish)──       publish_recovery_decision(incident, verdict)
dashboard
```
**The boundary:** we **read** evidence and **publish our verdict**. We never write machine state, never
close/re‑open anything on the host, and there is **no machine‑control method anywhere** (start/stop/PLC/
set‑point/alarm/interlock/LOTO) — enforced by an AST fitness test (`tests/test_architecture.py`).

## Read contract (consume) — domain → our DTO → suggested source
Every row is a real method on `EfficastPort`; `SyntheticEfficastPort` implements it for the demo,
`EfficastApiPort` is the `NotConfigured` skeleton for an authorized client.

| Domain | Port method | DTO | Suggested host source *(to confirm)* |
|---|---|---|---|
| Live telemetry | `get_machine_snapshot` | `MachineSnapshot` (vibration, temp, cycle time, scrap, fault) | REST `/machines/{id}/live` or MQTT |
| Historian back‑fill | *(telemetry seam, not the port)* | `TelemetrySample` → `app/services/telemetry.py` | bulk historian export → ingest endpoint |
| OEE | `get_oee_context` | `OEEContext` (availability · performance · quality · oee) | REST `/oee/{machine}` |
| Consumption | `get_consumption_snapshot` | `ConsumptionDTO` (energy · water · material) | REST `/consumption/{machine}` |
| MAIA / agent alerts | `get_open_alerts` · `acknowledge_alert` | `MaiaAlertDTO` | webhook or MQTT `agents/alerts` |
| Production order | `get_active_production_order` | `ProductionOrderDTO` | REST `/orders?machine={id}&status=active` |
| Machine events | `get_recent_machine_events` | `MachineEvent` | REST `/machines/{id}/events` |
| Quality / lots | `get_quality_status` · `get_affected_lots` | `QualityStatusDTO` · `LotDTO` | REST `/quality`, `/lots?order={id}` |
| Inventory (contingency part) | `get_inventory_status` | `InventoryStatusDTO` | REST `/inventory/{part}` |
| Schedule impact | `get_schedule_impact` | `ScheduleImpactDTO` | planner REST `/schedule/impact` |

## Publish contract (the only thing we write back)
| Action | Port method | Effect |
|---|---|---|
| Recovery verdict | `publish_recovery_decision(incident_id, decision, correlation_id)` | emits VERIFIED / REOPENED + the evidence summary — the host can surface it on WhatsApp / the dashboard |
| Agent event | `publish_agent_event(topic, payload, correlation_id)` | progress/audit events on the host's bus |

These are **events**, not commands. They carry no control instruction.

## To be agreed with the host (we do NOT assume these)
- **Auth**: API key / OAuth2 client‑credentials / mTLS — host's choice; we inject a client, never embed secrets.
- **Transport**: REST pull, MQTT/UNS subscribe, or webhook push — any combination; the port abstracts it.
- **Identifiers & fault taxonomy**: machine/sensor IDs and fault codes are the host's; we map them at the
  adapter edge (see the `_map_*` helpers in `efficast_api.py`).
- **Rate limits / pagination / granularity**: to be sized against the real API.

## What we'd hand over
1. **This spec** + the `EfficastPort` interface (real code, read‑only, no control surface).
2. A **working demo** on synthetic telemetry of the same shape (the cycle‑17 false‑recovery catch).
3. The **safety guarantees**, each backed by a test: no machine control (fitness test), the deterministic
   evaluator decides closure (not the LLM), every write through the gateway (allowlist invariant),
   tamper‑evident audit (delete/reorder detected), read‑only MCP.
4. The **composition root** (`app/composition.py`) — swapping `SyntheticEfficastPort` → `EfficastApiPort`
   is a one‑module change; nothing above the port moves.

**Honesty note:** customer names, funding, awards, and exact improvement percentages a partner might cite
are **not** asserted here — see the "NOT ASSERTED" row in [`EFFICAST_FIT.md`](EFFICAST_FIT.md). The pitch
stands on working, tested code and a verifiable wedge, not on unverifiable claims.
