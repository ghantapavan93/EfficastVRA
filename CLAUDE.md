# CLAUDE.md — operating guardrails for this repo

**Verified Recovery Agent** — an independent, Efficast‑aligned manufacturing‑AI prototype on **synthetic
data**. Thesis: *a closed work order ≠ a recovered line.* The agent verifies recovery **after** an
intervention via a deterministic **Recovery Contract**, and reopens on relapse. Not affiliated with the
real Efficast company; no partnership, integration, or API access is claimed.

## Frozen architectural decisions (do not change without explicit approval)
1. **No physical machine control — ever.** No start/stop/restart/PLC/set‑point/alarm/interlock/LOTO/
   auto‑quality‑release, not even mocked. Enforced by `gateway/actions.py:PROHIBITED_ACTIONS` and the AST
   fitness test `tests/test_architecture.py`.
2. **The deterministic evaluator owns closure, never the LLM.** `services/evaluator.py` is the sole verdict
   producer; the reasoning layer only proposes/explains and may not import the gateway.
3. **Every operational write goes through the Agent Action Gateway** (`gateway/gateway.py`), the single
   side‑effect choke point (schema→identity→plant→role→policy→human‑approval→idempotency→breaker→audit→
   execute→validate).
4. **Advisory layers stay advisory** — forecaster, decision intelligence, reliability statistics,
   sensitivity, provenance: read‑only, never change state.
5. **MCP server is read‑only** (`mcp_server.py`).
6. **Hexagonal boundaries** hold (composition root = `app/composition.py`); the host MES is reached only
   through `EfficastPort`.

## Integrity rules (this is the product's own thesis applied to itself)
- Tag every Efficast claim **VERIFIED / OBSERVED / INFERRED / UNKNOWN / PROTOTYPE_ASSUMPTION** (see
  `docs/EFFICAST_EVIDENCE_LEDGER.md`, `docs/RESEARCH_GAPS.md`). Never assert unverifiable specifics
  (clients, funding, awards, exact metrics, internal APIs) as fact.
- Cost/severity/threshold/SPRT figures are `PROTOTYPE_ASSUMPTION`s, env‑configurable, not real data.
- Prefer honest disclosure of gaps over overclaiming.

## How to run / test
- Backend: `cd backend && ./.venv/Scripts/python.exe -m app.cli reset && uvicorn app.main:app` (:8000).
  Tests: `./.venv/Scripts/python.exe -m pytest -q` (**181 passing**).
- Frontend: `cd frontend && npm run dev` (:3000, proxies `/api`). Checks: `npm run typecheck`, `npm run lint`,
  `npm run test` (**24 passing**), `npm run build`.
- Headless demo: `python -m app.cli demo`. Reset the DB after any model/audit‑hash change.

## Working agreement
Execute the **current phase in `docs/IMPLEMENTATION_PLAN.md`** in small, testable steps; preserve working
behavior; run the relevant tests after each unit; record completed work in the plan and unresolved
assumptions in `docs/RESEARCH_GAPS.md`. Commit/push only when the user asks. Don't expand scope or add
unrelated dependencies.
