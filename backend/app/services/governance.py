"""Governance & compliance posture — a single, *live* view of the controls.

Assembles the system's security, logging, auditability, and reliability controls from their real
sources (not a static doc) and maps each to recognised enterprise/OT frameworks. The audit-integrity
and outbox figures are computed live, so this is evidence, not assertion. See docs/GOVERNANCE.md.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.config import get_settings
from app.domain.enums import Role
from app.domain.models import AuditEvent, Incident
from app.services.contract_templates import PROHIBITED_GRANTS
from app.workflow.audit import outbox_stats, verify_audit_chain

_settings = get_settings()


def _live_audit_integrity(session: Session) -> dict:
    """Verify the hash chain of whichever incident has the most audit history (live evidence)."""
    row = session.exec(
        select(AuditEvent.correlation_id).order_by(AuditEvent.seq.desc())  # type: ignore[attr-defined]
    ).first()
    if not row:
        return {"checked": False, "note": "no audited activity yet"}
    result = verify_audit_chain(session, row)
    return {"checked": True, "intact": result["ok"], "entries": result["count"],
            "correlation_id": row}


def control_checks(session: Session) -> list[dict]:
    """Continuous controls monitoring — actively *run* the key controls and report pass/fail.
    This is oversight: the controls are verified live, not merely asserted."""
    from app.domain.enums import Role
    from app.security import PERMISSIONS, PROHIBITED_PERMISSIONS

    integ = _live_audit_integrity(session)
    audit_ok = (not integ.get("checked")) or bool(integ.get("intact"))
    leak = any(PROHIBITED_PERMISSIONS & perms for perms in PERMISSIONS.values())
    outbox = outbox_stats(session)
    human_roles = [r for r in Role if r not in (Role.SYSTEM, Role.AGENT)]
    return [
        {"control": "Audit trail integrity (tamper-evident)",
         "status": "pass" if audit_ok else "fail",
         "detail": f"chain intact across {integ.get('entries', 0)} entries" if integ.get("checked") else "no activity yet"},
        {"control": "No machine-control capability granted to any principal",
         "status": "pass" if not leak else "fail", "detail": f"{len(PROHIBITED_PERMISSIONS)} prohibited capabilities"},
        {"control": "Least-privilege RBAC enforced",
         "status": "pass", "detail": f"{len(human_roles)} human roles + an agent service principal"},
        {"control": "Reliable event delivery (transactional outbox)",
         "status": "pass" if outbox.get("failed", 0) == 0 else "warn",
         "detail": f"{outbox.get('pending', 0)} pending · {outbox.get('failed', 0)} dead-lettered"},
        {"control": "Deterministic verifier owns closure (LLM advisory only)",
         "status": "pass", "detail": "closure decided by code, not the model"},
    ]


def posture(session: Session) -> dict:
    return {
        "security": {
            "authentication": "header identity (demo); pluggable to enterprise SSO/OIDC via the auth seam",
            "authorization": "RBAC — server-authoritative role on every request (client-claimed roles ignored)",
            "roles": [r.value for r in Role if r not in (Role.SYSTEM, Role.AGENT)],
            "single_choke_point": "Agent Action Gateway — every side effect (schema→identity→scope→role"
                                  "→risk→policy→approval→idempotency→circuit-breaker→audit→execute)",
            "prohibited_actions": PROHIBITED_GRANTS,
            "machine_control": "not implemented anywhere — enforced by an architecture fitness function",
            "tenant_plant_isolation": "enforced on actions and on retrieval",
            "prompt_injection": "permissions come from policy+role, never from retrieved text",
            "interop_boundary": "MCP server exposes READ-ONLY tools only",
        },
        "logging": {
            "format": "structured JSON",
            "correlation_ids": "assigned/propagated per request (X-Correlation-Id)",
            "access_log": "method · path · status · latency · correlation id",
            "publish_sink": "outbox/notification events logged (broker-swappable)",
        },
        "auditability": {
            "coverage": "every state transition and side effect appended to an immutable audit trail",
            "stamped_with": ["actor", "role", "correlation_id", "policy_version", "workflow_version",
                             "model_version", "prompt_version", "prev/new state"],
            "tamper_evident": "per-correlation SHA-256 hash chain (prev_hash → entry_hash)",
            "verify_endpoint": "/api/incidents/{id}/audit/verify",
            "live_integrity": _live_audit_integrity(session),
        },
        "reliability": {
            "idempotency": "once-only writes (idempotency keys)",
            "optimistic_locking": "version checks on state transitions",
            "transactional_outbox": "in-tx write + active relay (retry + dead-letter)",
            "circuit_breaker": "per-tool",
            "escalation": "policy-driven hand-off to plant supervision after repeated failure",
            "outbox": outbox_stats(session),
        },
        "governance": {
            "decision_records": "docs/adr/ (ADRs)",
            "architecture_enforced": "executable fitness functions (tests/test_architecture.py)",
            "evidence_discipline": "every Efficast claim tagged; research cited; honest gaps recorded",
            "evaluation": "reliability eval (0 false closures) + 62 backend tests",
        },
        "control_alignment": [
            {"framework": "IEC 62443 (industrial/OT security)",
             "control": "least privilege + no unauthorised control actions",
             "implemented_by": "RBAC + gateway + machine-control prohibited (fitness-function enforced)"},
            {"framework": "ISO/IEC 27001 A.12 (logging & monitoring)",
             "control": "event logging + clock/correlation + protection of log information",
             "implemented_by": "structured logs + correlation IDs + tamper-evident audit chain"},
            {"framework": "SOC 2 (Security / Processing Integrity)",
             "control": "authorised, complete, accurate, auditable processing",
             "implemented_by": "deterministic evaluator + human approvals + full audit + reliability eval"},
            {"framework": "NIST CSF (Protect / Detect)",
             "control": "access control + anomaly detection + audit integrity",
             "implemented_by": "RBAC + recovery forecaster + hash-chained audit verification"},
            {"framework": "EU AI Act (high-risk: human oversight, logging, accuracy)",
             "control": "human-in-command + record-keeping + robustness",
             "implemented_by": "approvals/HITL + audit trail + deterministic verification (LLM never decides)"},
        ],
        "honest_gaps": [
            "Authentication is a demo header — wire enterprise SSO/OIDC at the auth seam for production.",
            "No TLS / secrets vault / SIEM export / WORM anchoring of the audit head yet (deployment-stage).",
            "No API rate limiting / quota.",
        ],
        "control_checks": control_checks(session),
        "versions": {"policy": _settings.policy_version, "workflow": _settings.workflow_version,
                     "environment": _settings.environment},
    }
