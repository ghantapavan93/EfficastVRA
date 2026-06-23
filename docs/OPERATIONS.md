# Operations — support ownership & uptime expectations

How this service is run: service levels, who owns what, on-call, and the operational signals. (Targets
are reference objectives for a real deployment; the prototype runs on SQLite with no SLA.)

## Service-level objectives (reference)
| SLI (measured) | Where | SLO |
|---|---|---|
| Availability | `/health` (deep: DB + outbox) | 99.9% monthly |
| API latency (read) | `/api/metrics` `latency_ms.p95` | p95 < 300 ms |
| API error rate | `/api/metrics` `error_rate` (5xx) | < 0.5% |
| Event-delivery backlog | `/api/metrics` → outbox / `/api/governance` | 0 dead-lettered; pending drains < 60 s |
| Audit integrity | `/api/incidents/{id}/audit/verify` | always intact (any break = Sev-1) |

**Error budget:** 0.1% / month. When the budget is burning, feature rollout pauses and reliability work
takes priority (standard SRE practice).

## Ownership (RACI)
| Area | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Platform availability / SLOs | SRE on-call | Eng lead | Plant IT | Plant ops |
| Agent decision quality (evals) | ML/agent owner | Eng lead | Reliability eng | QA |
| Security & compliance controls | Security owner | CISO | SRE | Auditors |
| A manufacturing **incident** (in-product) | the role on the mission (`owner`) | Plant supervisor | Quality, Technician | MAIA / agent |
| Knowledge candidates | Reliability engineer (reviewer) | Eng manager | — | Shift leads |

The product encodes the *in-product* ownership directly: every mission has a current **owner** and a
**next required action**, and policy **escalation** hands an incident to plant supervision after repeated
failure — so operational ownership is explicit and auditable, not tribal.

## On-call & support tiers
- **Tier 1 (plant):** Worker/Quality/Supervisor act on **notifications** (the agent pushes the next task;
  WhatsApp/email in production). They never need to "go hunting".
- **Tier 2 (SRE on-call):** owns availability/latency/error-budget; watches `/api/metrics`, `/health`,
  `/api/governance` (continuous control checks).
- **Tier 3 (eng/security):** agent-quality regressions, security-control failures, post-mortems.

## Operational signals (single pane)
- **Health:** `GET /health` → `status` + `db` + outbox stats. Degraded ⇒ page Tier 2.
- **Metrics/SLIs:** `GET /api/metrics` (uptime, requests/errors, p50/p95/p99, mission KPIs) — System page.
- **Controls:** `GET /api/governance` `control_checks` (live pass/fail) — System page.
- **Audit integrity:** the "tamper-evident · verified" badge + the verify endpoint.

## Change management
Migrations are versioned; the seed/reset is one command; deterministic scenario replay makes
regressions reproducible; the architecture **fitness functions** + 66 backend tests gate every change.
Releases are pinned by `policy_version` / `workflow_version`, stamped on every audit row.

See [`INCIDENT_RESPONSE.md`](INCIDENT_RESPONSE.md) for the runbook and
[`PRODUCTION_EVOLUTION.md`](PRODUCTION_EVOLUTION.md) for the hardening path.
