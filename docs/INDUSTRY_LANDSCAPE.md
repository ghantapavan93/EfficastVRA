# Industry landscape — how real platforms deliver AI agents to machinery

Independent web research (2026-06-22) into how production industrial-AI platforms connect to plant
machinery and deliver agents on top — and what we adopt. The field has converged on one shape, and it
is exactly the boundary this prototype already draws.

## The platforms
- **Efficast** ([efficast.ai](https://efficast.ai/en/homes/)) — connects *any* machine (2005-era to new)
  via PLCs/sensors/direct cable, installs in a day; AI agents build reports, close work orders, alert
  bottlenecks, and answer "how are we doing?"; an AI supervisor on WhatsApp. The agent is a **reasoning
  layer above the MES** — it augments, it doesn't replace.
- **Siemens Industrial Copilot** ([siemens.com](https://www.siemens.com/en-us/company/insights/generative-ai-industrial-copilot/),
  [press](https://press.siemens.com/global/en/pressrelease/siemens-expands-industrial-copilot-new-generative-ai-powered-maintenance-offering)) —
  Siemens domain platform (Xcelerator) + Microsoft Azure OpenAI; **Senseye Predictive Maintenance** +
  a Maintenance Copilot (AI repair guidance + condition monitoring); 100+ companies (Schaeffler,
  thyssenkrupp). Delivery = domain platform + cloud LLM + sensor connectivity + human-in-the-loop copilot.
- **Cognite Data Fusion / Atlas AI** ([cognite.com](https://www.cognite.com/en/industrial-ai),
  [contextualization](https://www.cognite.com/en/resources/blog/unlocking-operational-intelligence-from-contextualization-to-industrial-ai-at-scale)) —
  an **industrial data fabric**: ~100 connectors (incl. **OPC-UA** and an **OSIsoft PI** extractor,
  [docs](https://docs.cognite.com/cdf/integration/guides/extraction/pi)) feed a single source of truth;
  an **Industrial Knowledge Graph** contextualizes OT/IT/ET data so "AI agents are grounded in factual,
  contextualized data, minimizing incorrect outputs."
- **Bosch Shopfloor Agent** ([bosch.com](https://www.bosch.com/stories/agentic-ai-manufacturing-production/)),
  **Critical Manufacturing** ([Automation World](https://www.automationworld.com/analytics/article/55308436/critical-manufacturing-how-ai-agents-will-transform-mes-and-manufacturing)) —
  agentic AI as the **reasoning layer above the MES**, same thesis.

## The cross-cutting architecture (what they all do)
1. **ISA-95 asset hierarchy** ([HiveMQ](https://www.hivemq.com/resources/smart-manufacturing-using-isa95-mqtt-sparkplug-and-uns/)):
   *Enterprise → Site → Area → Line → Cell* (ISA-95 Part 2) is the shared model for a plant.
2. **Unified Namespace (UNS)** ([SymphonyAI](https://www.symphonyai.com/industrial/unified-namespace-complete-guide/),
   [IIoT World](https://www.iiot-world.com/smart-manufacturing/what-is-a-unified-namespace-and-how-does-it-work-in-manufacturing/)):
   an **MQTT broker as a central hub** replaces point-to-point "spaghetti" with hub-and-spoke; every
   system (PLC/SCADA/OEE, MES/ERP, engineering) publishes/subscribes on an ISA-95 topic hierarchy.
   *"A UNS provides the governed, contextualized data layer that AI systems require."*
3. **MQTT Sparkplug B** ([HiveMQ](https://www.hivemq.com/blog/implementing-unified-namespace-uns-mqtt-sparkplug/),
   [neomatrix](https://neomatrixinc.com/blog/sparkplug-b-or-not-to-b-unified-namespace-architecture-considerations/)):
   fixed topic `spBv1.0/Group_ID/Message_Type/Edge_Node_ID/[Device_ID]`; ISA-95 is mapped via the
   **Parris method** (`spBv1.0/Plant:Area:Line:Cell/NDATA/<edge>`). Plain-UNS topics look like
   `enterprise/site/area/line/cell/metrics/<signal>` (e.g. `GearCo/Munich/Stamping/Line1/Press3/metrics/HydraulicPressure`).
4. **Connector ecosystem** feeding the layer: OPC-UA, MQTT/Sparkplug, MES REST, historians (OSIsoft PI),
   ERP/CMMS — usually with **edge-to-cloud** extraction and historical backfill.
5. **Agent = reasoning layer above the MES/UNS**, with **human-in-the-loop** for consequential actions.

## What we adopt (and what we already had right)
| Pattern | In this prototype |
|---|---|
| Agent above the MES, not replacing it | `EfficastPort` boundary + bounded agent that only proposes |
| ISA-95 hierarchy | `app/integration/isa95.py` — Enterprise→Site→Area→Line→Machine→Component, derived from our entities |
| Unified Namespace topics | `uns_topic()` + Sparkplug-B (Parris) topic per machine signal |
| Connector ecosystem | `app/integration/connectors.py` — declarative catalog (OPC-UA, MQTT/UNS, MES REST, PI historian, CMMS) mapping to `EfficastPort`/`TelemetrySource` |
| Contextualized data the agent trusts | approval/recency-filtered RAG + provenance + the deterministic evaluator (the agent never trusts raw model output) |
| Real-data ingestion / historical backfill | the `TelemetrySource` seam ([REAL_DATA_INTEGRATION.md](REAL_DATA_INTEGRATION.md)) |
| Human-in-the-loop | approvals + the Agent Action Gateway; machine control is `PROHIBITED` |

See [`INTEGRATION_ARCHITECTURE.md`](INTEGRATION_ARCHITECTURE.md) for the implemented layer. We model the
UNS/connectors as a **documented, not-connected** integration surface (like `EfficastApiPort`) — this is
an independent prototype on synthetic data, not a live connection to any platform above.
