# Security Hardening — Defense-in-Depth

This layer sits **at the network edge and over the audit trail**, complementing (never replacing) the
Agent Action Gateway — the single authorization choke point for every side effect. Everything here is
live and self-reported at **`GET /api/security`** (`app/services/security_posture.py`), and verified by
`tests/test_security.py`. Limits are `PROTOTYPE_ASSUMPTION`s (our deployment choices, env-tunable) — not
claims about any external system.

## Controls

| Layer | Control | Where | Default |
|---|---|---|---|
| Edge | **Hardening response headers** — `Content-Security-Policy: default-src 'none'`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, COOP/CORP `same-origin`, `Permissions-Policy` (geo/mic/cam/pay/usb denied), generic `Server` | `app/security_http.py` | on |
| Edge | **Per-identity rate limiting** — fixed window keyed by `X-VRA-User` (else client IP); 429 + `Retry-After` + `X-RateLimit-*`; health/docs exempt | `app/rate_limit.py` | 600 / 60s |
| Edge | **Request body-size guard** — reject over the limit with 413 before routing | `app/security_http.py` | 1 MiB |
| Audit | **Tamper-evident hash chain** — per-correlation SHA-256 (`prev_hash → entry_hash`) over content + attribution | `app/workflow/audit.py` | on |
| Audit | **Keyed signing (HMAC-SHA256)** over each `entry_hash` — unforgeable without the secret; `verify_audit_chain` reports `authenticated` | `app/workflow/audit.py` | off until `VRA_AUDIT_HMAC_KEY` set |
| Detection | **Classified security-event stream** — every gateway denial + edge block emits a severity-ranked event (info/warning/critical) to a structured JSON log (SIEM-ready) + an in-process ring for the posture view | `app/security_events.py` | on |

### Why HMAC signing matters
The SHA-256 hash chain is **public**: an attacker who can rewrite the DB can recompute it and re-link a
forged chain. The HMAC signature is **keyed** — without `VRA_AUDIT_HMAC_KEY` they cannot reproduce
`entry_hmac`, so `verify_audit_chain` returns `authenticated: false`. Hash chain = *detects accidental/
unprivileged tampering*; keyed signature = *detects a privileged forger*.

### Security-event taxonomy
Gateway denial **stage → kind / severity**: `risk_class → prohibited_action_attempt / critical`,
`plant_scope → cross_tenant_attempt / critical`, `human_approval → non_human_approval_attempt / critical`,
`identity → unauthenticated_attempt`, `role → insufficient_role`, `policy → policy_violation`,
`circuit_breaker → circuit_open`, `rate_limit → rate_limit_exceeded`. Edge: `oversized_request`.

## Framework alignment
OWASP ASVS (V14 config / V13 API) · OWASP API Security Top 10 (API4 resource consumption, API8 misconfig)
· NIST CSF **Detect** (DE.CM/DE.AE) · ISO/IEC 27001 A.12.4 / A.16 (protected logs + security events) ·
IEC 62443 (least privilege, no unauthorised control).

## Honest gaps (disclosed, not hidden)
- Rate limiting + the event ring are **per-instance / in-memory** — use Redis + a SIEM for shared
  multi-instance quotas and durable, queryable detection.
- The audit-signing key is read from an **env var** and **off by default** — source it from a vault/KMS
  and rotate it in production.
- **TLS termination + HSTS** are deployment-stage (`VRA_SECURITY_HSTS=1` once TLS terminates here).
- Authentication is still a **demo identity header** — wire enterprise SSO/OIDC at the auth seam.

See [`THREAT_MODEL.md`](THREAT_MODEL.md) (T13–T17) and [`GOVERNANCE.md`](GOVERNANCE.md). This hardening
does **not** widen the agent's authority: no new write path, no machine control — purely rejection,
detection, and tamper-evidence.
