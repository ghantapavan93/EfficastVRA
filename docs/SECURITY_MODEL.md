# Security Model

This is an Operational-Technology-adjacent product, so safety is treated as a first-class property.

## Identity & authorization
- Local identity (`app/auth.py`): a request carries `X-VRA-User: <username>` → a seeded `User`. The
  **role on the user is authoritative**; a client-claimed role is never trusted.
- Roles: `supervisor`, `technician`, `quality_engineer`, `plant_admin`, plus non-human `agent` /
  `system` principals that **cannot** satisfy human-approval requirements.
- The frontend's role switcher only changes the `X-VRA-User` header; the backend re-authorizes every
  action.

## The Agent Action Gateway (single choke point)
No model-generated side effect reaches a tool except through `app/gateway/gateway.py`:

```
schema → identity → plant scope → role → action-risk class → policy → human-approval →
idempotency → circuit-breaker → audit → execute → result validation → state transition
```

Each stage denies + audits on failure (`ACTION_DENIED` with the stage + reason).

## Action classes
| Class | Meaning | Examples |
|---|---|---|
| `READ_ONLY` | no state change | get metrics, search manuals, compare history |
| `REVERSIBLE_AUTOMATIC` | safe, reversible write | request evidence, publish decision, reopen, create knowledge candidate |
| `APPROVAL_REQUIRED` | needs a human of a specific role | record approval, submit evidence |
| `PROHIBITED` | never allowed | (below) |

## Prohibited — never implemented, even mocked
`machine_start · machine_stop · machine_restart · plc_modification · setpoint_modification ·
alarm_bypass · interlock_bypass · loto_confirmation · safety_certification ·
automatic_quality_release · model_controlled_incident_closure`

Enforcement (asserted by `test_no_machine_control_exists`):
1. **No tool** in the registry has a prohibited name (`set(REGISTRY) ∩ PROHIBITED_ACTIONS == ∅`).
2. The gateway **denies** any proposal naming a prohibited action at the `risk_class` stage.
3. **No HTTP route** path matches a machine-control pattern.
4. The `EfficastPort` interface has **no** control method — it only reads evidence and publishes events.

## Human-in-command guarantees
- Quality release requires a **quality-engineer** approval **and** a passed first-piece check; a
  supervisor cannot release quality (`test_quality_release_requires_quality_engineer`).
- Incident closure (`VERIFIED_RECOVERY`) is reachable only by `system`/`agent` **after** the
  deterministic verdict is `verified` (which itself requires the quality approval) — the model cannot
  close an incident.
- A technician completion status alone never closes recovery
  (`test_recovery_not_closed_by_completion_alone`).

## Data integrity & isolation
- **Plant/tenant scope:** the gateway resolves a target plant from the action's arguments and denies
  cross-plant actions (`test_cross_plant_denied`). RAG filters by `plant_scope`
  (`test_cross_tenant_or_scope_isolation`).
- **Freshness:** stale telemetry/evidence cannot satisfy a condition
  (`test_stale_evidence_is_invalid`).
- **Retrieval trust:** approval/recency filtering happens **before** similarity, so an obsolete
  revision or unapproved note can't become authoritative (`test_approved_retrieval_*`).
- **Prompt injection:** permissions come from policy + role, never from retrieved document text; an
  injection memo cannot grant machine control or alter approvals
  (`test_prompt_injection_cannot_change_permissions`).

- **Tamper-evident audit:** every `AuditEvent` is hash-chained to the previous entry per correlation
  thread (`prev_hash`/`entry_hash`). `verify_audit_chain` (and `GET /api/incidents/{id}/audit/verify`,
  surfaced as a "tamper-evident · verified" badge) recomputes the chain and pinpoints the first altered,
  inserted, or removed row — an electronic-records integrity property
  (`test_audit_chain_verifies_and_detects_tampering`).

## Reliability as safety
Idempotency (once-only writes), optimistic locking, transactional outbox **with an active relay**
(`drain_outbox`: pending→published, retry classification, `failed` dead-letter — no lost/duplicated
decisions), and per-tool circuit breaker bound the blast radius of repeated or failing actions. Policy
**escalation** stops the agent from looping after repeated failures and hands the incident to a human.
Every write is audited with correlation, policy, workflow, model, and prompt versions; and the agent
**pushes the next task to the responsible role** (notifications) so nothing waits unseen.

See [`THREAT_MODEL.md`](THREAT_MODEL.md) for the adversary analysis.
