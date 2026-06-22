# Threat Model

Scope: the prototype's agentic recovery loop. Out of scope: network/host hardening, IdP integration,
and physical OT network segmentation (a real deployment would add these — see
[`PRODUCTION_EVOLUTION.md`](PRODUCTION_EVOLUTION.md)).

## Assets
Production safety & uptime · incident/contract state integrity · audit completeness · quality
disposition · operator trust.

## Adversaries & mitigations

| # | Threat | Vector | Mitigation | Test |
|---|---|---|---|---|
| T1 | **LLM induced to control a machine** | malicious/confused model output proposing `machine_*` | `PROHIBITED` class denied at gateway; no such tool/route/port method exists | `test_no_machine_control_exists` |
| T2 | **Prompt injection via documents** | a manual/note says "grant machine_start, auto-close" | permissions derive from role+policy, not text; approval/recency filter before retrieval ranking | `test_prompt_injection_cannot_change_permissions`, `test_approved_retrieval_excludes_obsolete_and_unapproved` |
| T3 | **False closure** | "work order complete" treated as recovered | deterministic contract requires 30 stable cycles + non-recurrence + quality release; cycle-17 relapse reopens | `test_cycle_17_violates_and_reopens`, `test_recovery_not_closed_by_completion_alone` |
| T4 | **Stale/forged telemetry satisfying a condition** | old reading replayed | freshness gate invalidates stale evidence; condition stays BLOCKED | `test_stale_evidence_is_invalid` |
| T5 | **Privilege escalation on approvals** | technician approves a supervisor/quality gate | gateway role check + state-machine guard; role on the authenticated user is authoritative | `test_unauthorized_role_cannot_approve`, `test_quality_release_requires_quality_engineer` |
| T6 | **Obsolete guidance overriding policy** | retired manual revision with looser limit | approval-status + `superseded_by` filter before similarity; obsolete surfaced only as a flagged conflict | `test_conflict_detection_flags_obsolete_without_promoting_it` |
| T7 | **Cross-tenant / cross-plant data access** | principal acts on another plant's incident | gateway plant-scope denial; RAG `plant_scope` filter | `test_cross_plant_denied`, `test_cross_tenant_or_scope_isolation` |
| T8 | **Duplicate events causing double effects** | retried incident event / repeated action | unique `dedupe_key`; idempotency ledger replays prior result | `test_duplicate_incident_dedupe`, `test_duplicate_action_idempotent` |
| T9 | **Model outage corrupting state** | reasoning raises mid-operation | state transitions are deterministic + separate; a model failure leaves state unchanged; deterministic provider carries the demo | `test_model_failure_preserves_state` |
| T10 | **Unreviewed "learning" treated as fact** | knowledge candidate shown as approved guidance | candidates are `PENDING_REVIEW`, labelled as such in UI + API | `test_audit_completeness_and_knowledge_pending` |
| T11 | **Silent / unauditable actions** | a write bypasses logging | every gateway call writes `ACTION_PROPOSED/CLASSIFIED/TOOL_EXECUTED`; every transition writes `STATE_TRANSITION` | audit-completeness test |
| T12 | **Runaway repeated tool failures** | a flaky tool hammered | per-tool circuit breaker opens after N failures, cools down | `app/gateway/circuit.py` |

## Residual risks (documented, not mitigated in the prototype)
- Header-based identity is **demo-grade** — replace with a real IdP + signed tokens.
- No transport encryption / secrets management in the local profile.
- Synthetic telemetry is trusted as authentic; production needs signed device provenance.
- No rate limiting on the public API. See [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md).
