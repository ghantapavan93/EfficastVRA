# Repository Audit — Phase 0

**Date:** 2026-06-21
**Auditor:** Verified Recovery Agent build (principal-engineer role)
**Working dir:** `C:\Users\Pavan Kalyan\OneDrive\Documents\Desktop\Efficast`

## 1. Starting state (verified by direct inspection)

The directory was **greenfield** with respect to code. A `Glob **/*` returned only binary
reference assets — no source, no `package.json`, no `pyproject.toml`, no lockfiles, no `.git`:

| File | Type | Use |
|---|---|---|
| `home.webp` | screenshot | Efficast home/Inicio dashboard |
| `planner.webp` | screenshot | Production planner (Gantt) |
| `ordenes-de-produccion.webp` | screenshot | Production orders table |
| `worker.webp` | screenshot | Worker / Vista de Operario |
| `calidad.webp` | screenshot | Quality / Calidad |
| `stock.webp` | screenshot | Inventory / Stock |
| `reportes.webp` | screenshot | Reports / Reportes |
| `agentsv2.webp` | screenshot | AI agents grid (Maia, Mirko, …) |
| `download.png`, `Screenshot 2026-06-20 *.png` | screenshots | misc. product captures |

**Conclusion:** no existing stack, dependencies, tests, or license to preserve. We build from scratch.
The screenshots are treated as **primary-source design + product research** (see the Evidence Ledger).

## 2. Environment

- **Platform:** Windows 11, PowerShell primary shell (Git Bash also available).
- **Git:** the working directory is **not** a git repository at audit time.
- **Toolchain probe:** at audit time the command-safety classifier (a transient hosted dependency
  of the shell/web tools) was **temporarily unavailable**, so `python`/`node`/`docker` version
  probes and web research could not execute. File read/write was unaffected. This is logged as a
  gap in [`RESEARCH_GAPS.md`](RESEARCH_GAPS.md) and re-verified once the classifier recovered.
  Architecture was therefore chosen to be **toolchain-robust** (see §4).

## 3. Existing tests

None. (No code present.) New deterministic suites are introduced in Phase 6.

## 4. Stack decision & rationale

The brief's *preferred* stack (FastAPI/Pydantic/LangGraph/Postgres/pgvector/Next.js) is adopted,
with **graceful-degradation defaults** so the demo cannot fail for want of infrastructure:

| Concern | Default (zero-infra) | Production path | Why |
|---|---|---|---|
| Database | **SQLite** via SQLModel | PostgreSQL 16 + JSONB | Runs with no daemon; schema is portable |
| Vector search | **in-process numpy cosine** behind `RetrievalPort` | pgvector | RAG works without an extension build |
| Reasoning | **`DeterministicReasoningProvider`** (no key) | hosted/local LLM via same interface | Demo never depends on a model endpoint |
| Background work | **in-process durable worker** (DB-backed queue) | Dramatiq/Arq or Temporal | No broker required for a single-node demo |
| Object storage | **local filesystem** behind `ObjectStorePort` | MinIO/S3 | No extra service for document/photo evidence |
| Orchestration | **DB-backed state machine** with a Temporal-shaped interface | Temporal | Durable + replayable now, portable later |

Docker Compose is still provided (Postgres + pgvector + backend + frontend) as the production-shaped
option. **Kafka/Redpanda is intentionally excluded** — a transactional **outbox** table covers
reliable event publication for a single-node prototype; see
[`PRODUCTION_EVOLUTION.md`](PRODUCTION_EVOLUTION.md) for how a log/broker would slot in later.

## 5. Third-party libraries selected (smallest coherent stack)

**Backend:** `fastapi`, `uvicorn`, `sqlmodel` (→ SQLAlchemy + Pydantic v2), `pydantic`,
`numpy` (cosine retrieval), `httpx` (optional hosted reasoning), `pytest` (dev).
*LangGraph is wired behind the `ReasoningProvider`/agent-flow seam and is optional*; the deterministic
provider carries the demo so the core has **no hard LangGraph runtime dependency**.

**Frontend:** `next`, `react`, `typescript`, `tailwindcss`, `@tanstack/react-query`, `zod`,
`framer-motion` (single animation lib), `lucide-react` (icons), Radix primitives
(`@radix-ui/react-dialog`, `-tooltip`, etc.), `cmdk` (command palette). Charts use **hand-built SVG**
trajectory/sparkline components (no heavyweight chart lib) to keep the bundle small and the
expected-vs-actual visuals exact. No overlapping libraries (one motion lib, one data layer, one
primitive layer).

License posture for all of the above is recorded in [`LICENSE_AUDIT.md`](LICENSE_AUDIT.md).

## 6. Risks identified

- **No incremental execution during the classifier outage.** Mitigation: code authored in small,
  cohesive modules with strict typing; full install/migrate/test/run pass scheduled the moment the
  shell recovers (Phase 7).
- **Scope is very large.** Mitigation: depth-over-breadth — one workflow (PO-2841) end-to-end and
  correct, rather than a broad MES. Explicit non-goals in [`PRODUCT_SCOPE.md`](PRODUCT_SCOPE.md).
- **OneDrive-synced working directory** can lock files mid-write. Mitigation: `var/`, `node_modules/`,
  `.venv/` are git-ignored and kept out of sync-sensitive operations where possible.
