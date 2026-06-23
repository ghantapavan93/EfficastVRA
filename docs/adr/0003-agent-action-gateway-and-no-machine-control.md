# ADR 0003 — One gateway choke point for side effects; machine control is prohibited

**Status:** Accepted

## Context
This is an operational-technology context. A model-proposed side effect that reached a machine could
be catastrophic. We need a single, auditable place where every consequential action is authorized —
and hard guarantees that certain actions can never be expressed at all.

## Decision
- **Every** model-proposed side effect crosses the **Agent Action Gateway** (`app/gateway/`):
  schema → identity → plant scope → role → risk class → policy → human-approval → idempotency →
  circuit-breaker → audit → execute → result-validation → state-transition. Each stage denies + audits
  on failure.
- The operational **tool registry is importable only by the gateway** (the choke point) — agent and
  reasoning layers cannot reach it.
- Machine control (start/stop/restart, PLC/set-point write, alarm/interlock bypass, LOTO confirm,
  automatic quality release, model-driven closure) is **never implemented, even mocked** — there is no
  such port, route, tool, or function.

## Consequences
- Humans remain in command for all consequential actions; quality release and closure require the
  correct human role.
- Enforced by `test_architecture.py` (only the gateway imports the tool registry; no machine-control
  function exists anywhere) and by the safety/e2e tests.
- The blast radius of repeated/failing actions is bounded (idempotency + circuit breaker).
