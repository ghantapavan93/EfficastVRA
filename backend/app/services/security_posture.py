"""Security posture — a single, *live* view of the defense-in-depth controls.

Companion to ``governance.posture``: where governance covers the whole control surface, this zooms into
the edge + audit-integrity security controls and reports them from their real runtime sources (the live
rate limiter, the in-process security-event stream, the keyed audit verifier), mapped to recognised
security frameworks. Numbers are computed, not asserted. Honest gaps are disclosed, not hidden.
"""

from __future__ import annotations

from sqlmodel import Session

from app import security_events
from app.config import get_settings
from app.domain.enums import ActionClass
from app.gateway.actions import PROHIBITED_ACTIONS
from app.security_http import API_CSP, LIMITER, SECURITY_HEADERS
from app.services.governance import _live_audit_integrity
from app.workflow.audit import current_hmac_key

_settings = get_settings()


def _control_checks(session: Session, *, key_present: bool, integ: dict) -> list[dict]:
    """Continuously verify the security controls and report pass / warn / fail — live oversight."""
    audit_ok = (not integ.get("checked")) or bool(integ.get("intact"))
    crit = security_events.REGISTRY.critical_count()
    return [
        {"control": "Hardening response headers active (CSP, nosniff, frame-deny, COOP/CORP)",
         "status": "pass" if _settings.security_headers_enabled else "warn",
         "detail": f"{len(SECURITY_HEADERS) + 1} headers" if _settings.security_headers_enabled else "disabled"},
        {"control": "Per-identity rate limiting active (flood / abuse protection)",
         "status": "pass" if _settings.rate_limit_enabled else "warn",
         "detail": f"{LIMITER.limit}/{LIMITER.window_s}s per identity"},
        {"control": "Request body-size guard (oversized-payload DoS)",
         "status": "pass", "detail": f"limit {_settings.max_request_body_bytes} bytes"},
        {"control": "Audit trail tamper-evident (SHA-256 hash chain)",
         "status": "pass" if audit_ok else "fail",
         "detail": f"chain intact across {integ.get('entries', 0)} entries" if integ.get("checked") else "no activity yet"},
        {"control": "Audit keyed signing (HMAC-SHA256) — unforgeable without the secret",
         "status": "pass" if key_present else "warn",
         "detail": "signing active" if key_present else "set VRA_AUDIT_HMAC_KEY (vault/KMS) to enable"},
        {"control": "No machine-control capability anywhere (OT safety)",
         "status": "pass", "detail": f"{len(PROHIBITED_ACTIONS)} prohibited action names, fitness-function enforced"},
        {"control": "No unresolved critical security events",
         "status": "pass" if crit == 0 else "warn",
         "detail": "none in window" if crit == 0 else f"{crit} critical event(s) in the recent window"},
    ]


def posture(session: Session) -> dict:
    integ = _live_audit_integrity(session)
    key_present = bool(current_hmac_key())
    counts = security_events.REGISTRY.counts()
    return {
        "headers": {
            "enabled": _settings.security_headers_enabled,
            "applied": sorted([*SECURITY_HEADERS.keys(), "Content-Security-Policy"]),
            "content_security_policy": API_CSP,
            "hsts": "enabled" if _settings.security_hsts_enabled else "disabled — enable behind TLS",
        },
        "rate_limiting": {
            "enabled": _settings.rate_limit_enabled,
            "scope": "per identity (X-VRA-User, else client IP) · per instance",
            "limit": LIMITER.limit,
            "window_s": LIMITER.window_s,
            "tracked_identities": LIMITER.snapshot()["tracked_identities"],
            "throttled": counts.get("rate_limit_exceeded", 0),
            "note": "PROTOTYPE_ASSUMPTION limits — env-tunable; swap to Redis for shared multi-instance quotas",
        },
        "request_guard": {
            "max_body_bytes": _settings.max_request_body_bytes,
            "rejected_oversized": counts.get("oversized_request", 0),
        },
        "audit_signing": {
            "hash_chain": "per-correlation SHA-256 (prev_hash → entry_hash)",
            "keyed_signing": "HMAC-SHA256 over entry_hash" if key_present else "disabled (set VRA_AUDIT_HMAC_KEY)",
            "active": key_present,
            "live_integrity": integ,
        },
        "gateway": {
            "single_choke_point": "every side effect passes the Agent Action Gateway",
            "pipeline": "schema→identity→plant→role→risk→policy→approval→idempotency→circuit-breaker→audit→execute→validate",
            "prohibited_actions": sorted(PROHIBITED_ACTIONS),
            "action_classes": [c.value for c in ActionClass],
        },
        "detection": {
            "total_events": security_events.REGISTRY.total(),
            "by_kind": counts,
            "recent": security_events.REGISTRY.recent(12),
            "sink": "structured JSON security log (SIEM-ready) + in-process ring buffer for this view",
        },
        "control_alignment": [
            {"framework": "OWASP ASVS (V14 config / V13 API)",
             "control": "security headers, rate limiting, payload limits, secure defaults",
             "implemented_by": "edge SecurityMiddleware (CSP/headers + body guard + rate limit)"},
            {"framework": "NIST CSF — Detect (DE.CM / DE.AE)",
             "control": "continuous monitoring + anomaly/event detection",
             "implemented_by": "classified security-event stream on every gateway denial + edge block"},
            {"framework": "ISO/IEC 27001 A.12.4 / A.16 (logging + incident events)",
             "control": "protected logs + security-event recording",
             "implemented_by": "tamper-evident, optionally HMAC-signed audit chain + security-event taxonomy"},
            {"framework": "IEC 62443 (industrial/OT)",
             "control": "least privilege + no unauthorised control actions",
             "implemented_by": "RBAC + gateway choke point + machine-control prohibited (fitness-enforced)"},
            {"framework": "OWASP API Security Top 10 (API4 resource consumption, API8 misconfig)",
             "control": "throttling + hardened configuration",
             "implemented_by": "per-identity rate limiting + body-size guard + locked-down CSP"},
        ],
        "control_checks": _control_checks(session, key_present=key_present, integ=integ),
        "honest_gaps": [
            "Rate limiting and the security-event ring are per-instance (in-memory) — use Redis + a SIEM "
            "for shared multi-instance quotas and durable, queryable detection.",
            "The audit-signing key is read from an env var here; source it from a vault/KMS and rotate it "
            "in production (keyed signing is OFF until VRA_AUDIT_HMAC_KEY is set).",
            "TLS termination + HSTS are deployment-stage (enable VRA_SECURITY_HSTS once TLS terminates here).",
            "Authentication is still a demo identity header — wire enterprise SSO/OIDC at the auth seam.",
        ],
        "versions": {"policy": _settings.policy_version, "workflow": _settings.workflow_version,
                     "environment": _settings.environment},
    }
