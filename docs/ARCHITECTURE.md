# Architecture

Three deliberately separated systems behind one adapter boundary. The Large Language Model is never
the authoritative state store; deterministic code owns all decisions.

```
                          ┌─────────────────────────────────────────────┐
   Next.js (Forge UI) ───▶│  FastAPI HTTP API  (app/api)                 │
   reads real state       │  read views · gateway-mediated actions       │
                          └───────────────┬─────────────────────────────┘
                                          │
        ┌─────────────────────────────────┼──────────────────────────────────┐
        ▼                                 ▼                                    ▼
┌───────────────────┐      ┌──────────────────────────────┐      ┌────────────────────────┐
│ A. Manufacturing  │      │ B. Durable Operational        │      │ C. Bounded AI          │
│    Evidence       │◀────▶│    Workflow                   │◀────▶│    Reasoning           │
│ (SQLModel + DB)   │      │ state machine · evaluator ·   │      │ ReasoningProvider      │
│ machines, sensors,│      │ cycle engine · policy ·       │      │ (deterministic +       │
│ orders, lots,     │      │ reopening · audit · outbox ·  │      │ optional hosted) +     │
│ manuals, evidence │      │ idempotency · circuit breaker │      │ revision-aware RAG     │
└─────────┬─────────┘      └──────────────┬───────────────┘      └───────────┬────────────┘
          │                               │                                  │
          └────────────── EfficastPort (adapter boundary) ───────────────────┘
                          SyntheticEfficastPort (this prototype)
                                          │
                          Agent Action Gateway  (app/gateway)
              every operational side effect passes the full pipeline
```

## A. Manufacturing Evidence System (`app/domain`, `app/adapters`)
Owns the facts: `Plant, ProductionLine, Machine, Component, Sensor, ProductionOrder, Operator, Shift,
DowntimeEvent, ScrapEvent, QualityCheck, MaterialLot, InventoryPart, Technician, WorkOrder,
Intervention, Document/DocumentChunk, Incident (incl. historical), RecoveryObservation`. All access
to host-MES-like data crosses **`EfficastPort`**; `SyntheticEfficastPort` is the only implementation
here and contains the deterministic scenario physics (`ScenarioPhysics`) that produces the cycle-17
relapse. Swapping in a real `EfficastApiPort` requires no change to systems B or C.

## B. Durable Operational Workflow (`app/workflow`, `app/services`)
Owns process truth: the 16-state machine ([`STATE_MACHINE.md`](STATE_MACHINE.md)), the Recovery
Contract lifecycle, human approvals, evidence requests, verification windows, reopening, escalation,
the audit trail, idempotency, and the transactional outbox. The **recovery evaluator** and **cycle
engine** are pure deterministic services — they, not the model, decide pass / violated / verified.

## C. Bounded AI Reasoning (`app/reasoning`, `app/rag`)
Owns interpretation only: manual reading, recovery-requirement extraction, historical comparison,
missing-evidence identification, contract drafting/explanation, conflict explanation, summaries. The
`ReasoningProvider` interface has a `DeterministicReasoningProvider` (no key, carries the demo) and an
optional `HostedReasoningProvider` that only enriches narrative text and always falls back. RAG
filters by applicability + approval status **before** similarity ([`../docs/RECOVERY_CONTRACT.md`]).

## Agent Action Gateway (`app/gateway`)
The single choke point. No model-proposed side effect reaches a tool except through:

```
schema → identity → plant scope → role → action-risk class → policy → human-approval →
idempotency → circuit-breaker → audit(proposed/classified) → execute → result validation → transition
```

Action classes: `READ_ONLY`, `REVERSIBLE_AUTOMATIC`, `APPROVAL_REQUIRED`, `PROHIBITED`. The
`PROHIBITED` set (machine start/stop/restart, PLC/set-point change, alarm/interlock bypass, LOTO
confirmation, safety certification, automatic quality release, model-controlled closure) maps to **no
registered tool**, and any proposal naming one is denied + audited. See
[`SECURITY_MODEL.md`](SECURITY_MODEL.md).

## Data flow — the hero loop
1. Incident + completed intervention exist (seed).
2. Reasoning drafts the Recovery Contract spec → `contract_builder` persists conditions/evidence/
   approvals → state `RECOVERY_CONTRACT_DRAFTED`.
3. Gateway-mediated `request_missing_evidence`; humans submit evidence (validated for freshness +
   role); supervisor approves → `start_monitoring` opens window 1.
4. `cycle_engine.advance_cycle` ingests synthetic telemetry; `evaluator.evaluate` runs each cycle.
5. **Cycle 17:** F27 recurs → verdict `violated` → gateway `reopen_incident` preserves V1, drafts V2
   (bearing), parks at `CONTINGENCY_AWAITING_APPROVAL`.
6. Supervisor approves contingency (reserves BR-6205, assigns technician) → technician evidence →
   `complete_contingency` opens window 2.
7. 30 stable cycles + quality-engineer release → verdict `verified` → `VERIFIED_RECOVERY`, publish
   decision (outbox), create `KnowledgeCandidate` (PENDING_REVIEW).

Every step writes an `AuditEvent` with a monotonic per-correlation `seq` and policy/workflow/model/
prompt versions.

## Technology & runnability
FastAPI · SQLModel · Pydantic v2 · NumPy (cosine retrieval). **SQLite + in-process vector store by
default — zero infra.** PostgreSQL + pgvector is the documented production path (Docker Compose
provided). Deterministic reasoning needs no API key. Next.js 14 + TypeScript + Tailwind (Forge System)
+ TanStack Query + Radix + Framer Motion for the UI; it consumes backend truth only and duplicates no
business rule.

## Reliability
Idempotency ledger (once-only writes), optimistic locking on incident transitions, transactional
outbox for reliable event publication (no Kafka — see [`PRODUCTION_EVOLUTION.md`]), per-tool circuit
breaker, correlation IDs, health endpoints, deterministic seed/reset/replay, graceful model fallback.
