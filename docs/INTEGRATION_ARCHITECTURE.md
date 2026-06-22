# Integration architecture

How real plant data reaches the agent — modelled on the industry-standard stack
([`INDUSTRY_LANDSCAPE.md`](INDUSTRY_LANDSCAPE.md)) and implemented as **documented seams**, not live
connections (this is an independent synthetic prototype).

```
  PLCs / SCADA / sensors        MES (Efficast) / ERP / CMMS        historian (PI)
        │  OPC-UA                       │  REST                          │  extractor
        ▼                               ▼                                ▼
  ┌──────────────────────────── Unified Namespace (MQTT / Sparkplug B) ───────────────────────────┐
  │   ISA-95 topics:  enterprise / site / area / line / cell / metrics/<signal>                     │
  └───────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                                   │  (contextualised data layer)
        ┌──────────────────────────────────────────┼───────────────────────────────────────────────┐
        ▼                                           ▼                                                 ▼
   EfficastPort                              TelemetrySource                                 EfficastApiPort
 (snapshot, OEE, orders,                 (per-cycle readings for the                    (real MES mapping —
  quality, lots, MAIA alerts)             verification window)                           documented skeleton)
        └───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                                     ▼
                       Bounded agent (proposes)  ·  deterministic evaluator (judges)
                       ·  Agent Action Gateway (authorises)  ·  humans (decide & do)
                                       NO machine-control path anywhere
```

## ISA-95 hierarchy → UNS topics (`app/integration/isa95.py`)
We derive the ISA-95 path *Enterprise → Site → Area → Line → Cell* from existing entities and render
the topics a UNS broker would carry:
- UNS: `northstar/plant-ns/packaging-line-4/l4/l4-conv/metrics/vibration`
- Sparkplug B (Parris method): `spBv1.0/northstar:plant-ns:packaging-line-4:l4/NDATA/l4-conv`

This is the **contextualised addressing** AI agents need — the same scheme Cognite/HiveMQ/SymphonyAI
describe. Served (with the live example) at `GET /api/integration` and shown under System → Integration.

## Connector catalog (`app/integration/connectors.py`)
| Connector | Protocol | Direction | Feeds |
|---|---|---|---|
| OPC-UA server | OPC-UA | inbound | `TelemetrySource` + `get_machine_snapshot` |
| Unified Namespace | MQTT Sparkplug B | bidirectional | `TelemetrySource` (in) · `publish_*` (out) |
| MES REST (Efficast) | HTTPS/REST | bidirectional | `EfficastApiPort` |
| Process historian (PI) | PI Web API | inbound | `TelemetrySource` (+ backfill) |
| CMMS / ERP | HTTPS/REST | bidirectional | `EfficastPort` (inventory, work orders) |

Each is declarative and **documented, not connected**. Wiring a real deployment = pointing a connector
at a seam; the evaluator, gateway, workflow, and UI do not change. **No connector can carry a machine-
control command — the system has no such seam** (verified by `test_integration.py` and the no-machine-
control safety test).

## Why this is the transferable part
The valuable, reusable architecture for *any* operational-AI system: a **contextualised data layer
(ISA-95/UNS) + a typed port boundary + a deterministic verifier + a policy gateway + human-in-the-loop**.
The LLM is kept off the authority path; the data layer is governed and addressable; integration is
configuration, not a rewrite. See [`PRODUCTION_EVOLUTION.md`](PRODUCTION_EVOLUTION.md) for the broker /
edge / multi-tenant hardening path.
