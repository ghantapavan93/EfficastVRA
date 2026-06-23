# Incident response — *system* incident runbook

This is the runbook for incidents in the **software/security** sense (an outage, a control failure),
distinct from the manufacturing incidents the product itself manages. It maps each system incident to a
**concrete signal the platform already emits**, so detection is built in, not bolted on.

## Severity
- **Sev-1:** audit-integrity break, data-integrity loss, or full outage. Page immediately.
- **Sev-2:** elevated error rate / latency-SLO breach, outbox dead-lettering, circuit breaker stuck open.
- **Sev-3:** degraded but serving (e.g. hosted-model unavailable — deterministic fallback active).

## Lifecycle (detect → triage → contain → eradicate → recover → learn)
| Incident | Detection signal | Triage / contain | Eradicate / recover |
|---|---|---|---|
| **Audit tampering** | `verify_audit_chain` → `ok:false` (badge turns red; `/api/governance` control fails) | Sev-1. Freeze writes; the chain pinpoints `broken_at_seq` for forensics | Restore from backup before the break; rotate credentials; post-mortem |
| **Availability** | `/health` `status:degraded` (DB unreachable) | Page Tier 2; check DB/connection pool | Failover/restart; verify `/health` green |
| **Latency / error budget** | `/api/metrics` `p95` / `error_rate` over SLO | Identify hot path via correlation IDs in logs | Scale/roll back; resume rollout when budget recovers |
| **Event delivery** | outbox `failed` > 0 or `pending` not draining (`/api/metrics`, `/api/governance`) | Inspect dead-lettered events (they're retained, not lost) | Fix sink/broker; the relay re-publishes on recovery |
| **Tool failure** | per-tool **circuit breaker** opens (`CIRCUIT_OPENED` audit) | Breaker already contains it (fails safe, no side effect) | Fix the tool; breaker half-opens and recovers |
| **Agent reasoning unavailable** | hosted model errors / `REASONING_FALLBACK` audit | None — **deterministic provider takes over automatically** | Restore the hosted model; no workflow impact |
| **Unauthorized-action attempt** | gateway `ACTION_DENIED` audit (stage + reason) | Already blocked; review the actor/correlation | Tighten policy/role if warranted |

## Guarantees that bound the blast radius
Idempotency (no duplicate effects on retry), optimistic locking (no lost updates), the transactional
outbox (no lost/duplicated decisions), per-tool circuit breakers, and **machine control that cannot
exist** mean most failure modes fail *safe*. Every step of every incident is itself captured in the
tamper-evident audit trail — so the post-mortem has ground truth.

## Forensics & post-mortem
Each audit row carries actor, role, correlation id, and policy/workflow/model/prompt versions; the hash
chain proves the record wasn't altered. Filter by `correlation_id` to reconstruct an exact timeline.
Every Sev-1/Sev-2 gets a blameless post-mortem with an action item that becomes a test or a fitness
function (so the same incident can't recur silently).
