# Efficast Integration — Open Questions

*The honest list of what we would need **from Efficast** to move from "integration-ready" to "integrated."
Until these are answered and a real endpoint or sanitised dataset is provided and tested, the `Sandbox`
adapter stays unwired and we do not claim a connection. Each item is tagged UNKNOWN (we have no Efficast
access) unless noted.*

## Access & security
- **Auth model** — OAuth2 client-credentials, API key, or mTLS? Token lifetime, scopes? *(UNKNOWN)*
- **Tenancy** — how are tenant/plant identified and isolated on their side? Does one credential span plants? *(UNKNOWN)*
- **Network** — public REST, private VPC peering, or on-prem edge? Egress/firewall constraints? *(UNKNOWN)*
- **Rate limits / quotas / pagination** for reads. *(UNKNOWN)*

## Data shape & mapping
- **Their event/entity schemas** — the real field names/types for machine events, telemetry, cycles,
  orders, work orders, interventions, quality, lots, approvals. Our v0.1 contract is our *target*; we need
  their source schema to author the `mapping_version`. *(UNKNOWN)*
- **Identifiers** — stable IDs for machine, sensor, order, lot, work order, intervention? Are they globally
  unique or plant-scoped? *(UNKNOWN)*
- **Units & baselines** — canonical units per metric; where do baselines/thresholds come from? *(UNKNOWN)*
- **Time** — do events carry origin timestamps + timezone? Expected clock skew? *(UNKNOWN)*

## Delivery semantics (drives reconciliation)
- **Push or pull?** Webhooks, an event stream (Kafka/MQTT/Sparkplug?), or polling REST? *(UNKNOWN)*
- **Idempotency** — does Efficast provide a stable per-event id we can use as `idempotency_key`? Delivery
  guarantee (at-least-once?), retry/replay behaviour? *(UNKNOWN)*
- **Ordering** — are events ordered per stream/partition, or can they arrive late/out-of-order? *(UNKNOWN)*

## Domain semantics
- **Sensor health / calibration** — is sensor calibration status / replacement available? (needed to *derive*
  the Sensor Trust Gate rather than read a declared status). *(UNKNOWN)*
- **Lot model** — lot↔order↔cycle linkage + production-time windows (needed for Lot-at-Risk). *(UNKNOWN)*
- **Quality model** — first-piece / SPC results, hold/release events, MRB disposition. *(UNKNOWN)*
- **Approvals** — how human approvals (supervisor/quality) are represented and authenticated. *(UNKNOWN)*

## Outbound (proposals)
- **Proposal channel** — how should `request_evidence` / `propose_incident_reopen` /
  `publish_recovery_status` / `create_recovery_debt_proposal` reach Efficast? A REST endpoint, a topic, a
  MAIA message? **What we will never do:** start/stop machines, change setpoints, bypass interlocks, or
  auto-release quality — those are out of scope by design. *(UNKNOWN)*
- **MAIA** — is there an outbound channel to MAIA for structured status messages, and what format? *(UNKNOWN)*

## What we can do *today*, without any of the above
Run **shadow mode** over a **sanitised** event bundle (synthetic now, a real sanitised export later):
evaluate, propose, compare to the actual outcome, write nothing. That is the bridge — and the evidence — that
precedes any live connection. See `REAL_DATA_PILOT_PLAN.md`.
