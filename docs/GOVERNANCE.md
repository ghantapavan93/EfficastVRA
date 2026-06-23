# Governance, security, logging & auditability

> **Checking the claim "no security, no logging, no auditability."** For this system that is inverted —
> they are its core. Below is the evidence (with code/test references), the live posture
> (`GET /api/governance`, and the System → Governance & Compliance panel), and an honest list of the
> real *enterprise-deployment* gaps that remain.

## Security — present
- **RBAC, server-authoritative.** Roles (supervisor · technician · quality_engineer · plant_admin) are
  read from the seeded user, never from a client-claimed value (`app/auth.py`). State transitions are
  role-guarded (`app/workflow/state_machine.py`). Test: `test_unauthorized_role_cannot_approve`.
- **One choke point.** Every side effect crosses the **Agent Action Gateway** — schema → identity →
  plant scope → role → risk class → policy → human-approval → idempotency → circuit-breaker → audit →
  execute → result-validation (`app/gateway/`).
- **Prohibited actions.** Machine start/stop/restart, PLC/set-point write, alarm/interlock bypass,
  LOTO confirm, automatic quality release, model-driven closure are **never implemented** — and an
  **architecture fitness function** fails the build if any such function appears
  (`tests/test_architecture.py`).
- **Isolation.** Tenant + plant scope enforced on actions and on retrieval
  (`test_cross_plant_denied`, `test_cross_tenant_or_scope_isolation`).
- **Prompt-injection resistant.** Permissions come from policy + role, never from retrieved document
  text (`test_prompt_injection_cannot_change_permissions`).
- **Read-only interop.** The MCP server exposes only read tools (`tests/test_mcp.py`).

## Logging — present
- **Structured JSON logging** (`app/main.py`), **correlation IDs** assigned/propagated per request
  (`X-Correlation-Id`), and a per-request **access log** (method · path · status · latency · cid).
  Event publish + notifications are logged through swappable sinks.

## Auditability — present (and tamper-evident)
- **Every** state transition and side effect is appended to an immutable audit trail, stamped with
  actor, role, correlation id, and **policy / workflow / model / prompt versions** (`app/workflow/audit.py`).
- The trail is **tamper-evident**: a per-correlation **SHA-256 hash chain** (`prev_hash → entry_hash`).
  `verify_audit_chain` (and `GET /api/incidents/{id}/audit/verify`, shown as a "tamper-evident · verified"
  badge) recomputes the chain and pinpoints any altered/inserted/removed row
  (`test_audit_chain_verifies_and_detects_tampering`).

## Control-framework alignment (maps to, not certified)
| Framework | Control | Implemented by |
|---|---|---|
| **IEC 62443** (OT security) | least privilege; no unauthorised control | RBAC + gateway + machine-control prohibited (enforced) |
| **ISO/IEC 27001 A.12** | event logging, clock/correlation, log protection | structured logs + correlation IDs + hash-chained audit |
| **SOC 2** (Security / Processing Integrity) | authorised, complete, accurate, auditable | deterministic evaluator + approvals + full audit + eval |
| **NIST CSF** (Protect / Detect) | access control + anomaly detection + integrity | RBAC + recovery forecaster + audit verification |
| **EU AI Act** (high-risk) | human oversight, record-keeping, robustness | HITL approvals + audit trail + LLM-never-decides |

## Governance & structure
ADRs (`docs/adr/`), a C4 model (`docs/ARCHITECTURE.md`), **executable architecture fitness functions**,
hexagonal ports + a composition root, an evidence ledger, a reliability eval, and 62 backend tests.

## Honest enterprise-deployment gaps (not yet done)
1. **Authentication** is a demo `X-VRA-User` header — wire enterprise **SSO/OIDC** at the auth seam.
2. No **TLS**, **secrets vault**, **SIEM/log export**, or **WORM/external anchoring** of the audit
   chain head (deployment-stage hardening — see [`PRODUCTION_EVOLUTION.md`](PRODUCTION_EVOLUTION.md)).
3. No API **rate limiting / quotas**.

These are disclosed deliberately (the project tags every claim and records its gaps). The *controls*
exist and are live; the *production hardening* of identity/transport/retention is the remaining work.
