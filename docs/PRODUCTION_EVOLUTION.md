# Production Evolution

How each prototype choice maps to a production-grade implementation **without rewriting the core** —
the seams were built for this.

## 1. Real Efficast integration (the adapter seam)
Replace `SyntheticEfficastPort` with an authorized `EfficastApiPort` implementing the same
`EfficastPort` interface. Systems B (workflow) and C (reasoning) are untouched. The synthetic
`ScenarioPhysics` disappears entirely; telemetry arrives from Efficast Edge. *Requires Efficast's real
API, which is `UNKNOWN` to this prototype — do not assume the method shapes here match theirs.*

## 2. Durable workflow → Temporal
The state machine already exposes a single `transition()` entry point with explicit pre/postconditions
and an audit side effect. Wrap each operation as a **Temporal** activity and model the lifecycle as a
Temporal workflow: free retries, timeouts, heartbeats, durable timers (real verification-window
clocks), and replayable history. The DB-backed state becomes Temporal's event history; the audit trail
remains for the operational record.

## 3. Database → PostgreSQL + pgvector
Set `VRA_DATABASE_URL=postgresql+psycopg://…`; the SQLModel schema is portable. Move JSON columns to
JSONB (already compatible). Swap the NumPy `RetrievalPort` for **pgvector** with real embeddings
(e.g., a hosted embedding model) — only `app/rag/embeddings.py` + `retrieval.py` change; the
applicability/approval-before-similarity contract stays.

## 4. Reasoning → hosted/local model
`HostedReasoningProvider` already calls an Anthropic-compatible Messages API and falls back to
deterministic output. For production: keep deterministic code as the **authority** (contract
evaluation, permissions), use the model for drafting/explanation, add structured-output validation and
prompt/version pinning (already tracked in the audit trail). If LangGraph is adopted, use the
**MIT-licensed libraries** directly and avoid the Elastic-licensed `langgraph-api` server (see
[`LICENSE_AUDIT.md`](LICENSE_AUDIT.md)).

## 5. Eventing → broker (only when needed)
The **transactional outbox** is already in place, so adding a real bus is incremental: a relay process
tails `OutboxEvent` and publishes to **Kafka / Redpanda / NATS**, marking rows published (at-least-once
with idempotent consumers). No application code changes — the outbox decouples state changes from
delivery. Kafka was intentionally **not** added now (a single-node prototype doesn't need it).

## 6. Background work → durable worker
Replace the in-process drain with **Dramatiq / Arq / Celery** (or Temporal activities) for evidence
timeouts, window timers, outbox publication, and retries — DLQ / explicit `failed`-state handling and retry
classification scaffolding already exist.

## 7. Identity & security
Swap header identity for an **OIDC/SAML IdP** with signed, short-lived tokens and per-plant RBAC.
Add transport encryption, secrets management, rate limiting, audit log shipping (SIEM), and
device-signed telemetry provenance. The Agent Action Gateway stays as the authorization choke point.

## 8. Object storage → MinIO/S3
Evidence files/photos move behind an `ObjectStorePort` to MinIO/S3 with signed URLs (the local
filesystem implementation is the dev stand-in).

## 9. Observability
Structured JSON logging + correlation IDs exist. Add **OpenTelemetry** traces/metrics across the
gateway pipeline and workflow transitions, dashboards on contract verdicts / reopen rates / time-in-
state, and alerting on circuit-breaker opens and DLQ growth.

## 10. Knowledge loop
`KnowledgeCandidate` rows are `PENDING_REVIEW`. Production adds a human expert-review queue; approved
knowledge feeds back into the **approved** RAG corpus (with effective dates + supersession), closing
the tribal-knowledge transfer loop the challenge targets.
