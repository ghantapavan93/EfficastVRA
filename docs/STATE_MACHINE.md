# Recovery Workflow State Machine

Implemented in `app/workflow/state_machine.py`. Pure-Python transition table + role guards; every
transition validates current state → legality → role, applies an optimistic-lock version check, and
appends a `STATE_TRANSITION` audit row. The interface is Temporal-shaped (a single `transition()`
entry point a future Temporal activity could wrap unchanged).

## States (18)
`ALERT_TRIAGED · INTERVENTION_PROPOSED · INTERVENTION_RECORDED · RECOVERY_CONTRACT_DRAFTED ·
RECOVERY_CONTRACT_REVIEWED · AWAITING_REQUIRED_EVIDENCE · READY_FOR_MONITORING · MONITORING_RECOVERY ·
RECOVERY_CONDITION_PENDING · RECOVERY_CONDITION_FAILED · INSUFFICIENT_EVIDENCE · RECOVERY_FAILED ·
INCIDENT_REOPENED · CONTINGENCY_AWAITING_APPROVAL · CONTINGENCY_IN_PROGRESS · VERIFIED_RECOVERY ·
ESCALATED · CANCELLED`

The first two are the **front of the loop** (Phase 9): a MAIA-style alert is triaged by the agent
(`ALERT_TRIAGED`), which proposes an intervention (`INTERVENTION_PROPOSED`) that a human accepts to
reach `INTERVENTION_RECORDED` — the original entry point. Everything downstream is unchanged.

Terminal: `VERIFIED_RECOVERY`, `ESCALATED`, `CANCELLED`.

## Legal transitions
```
ALERT_TRIAGED                → INTERVENTION_PROPOSED | CANCELLED          (agent triages a MAIA alert)
INTERVENTION_PROPOSED        → INTERVENTION_RECORDED | CANCELLED          (supervisor accepts diagnosis)
INTERVENTION_RECORDED        → RECOVERY_CONTRACT_DRAFTED | CANCELLED
RECOVERY_CONTRACT_DRAFTED    → RECOVERY_CONTRACT_REVIEWED | CANCELLED
RECOVERY_CONTRACT_REVIEWED   → AWAITING_REQUIRED_EVIDENCE | CANCELLED
AWAITING_REQUIRED_EVIDENCE   → READY_FOR_MONITORING | INSUFFICIENT_EVIDENCE | CANCELLED
READY_FOR_MONITORING         → MONITORING_RECOVERY | CANCELLED
MONITORING_RECOVERY          → MONITORING_RECOVERY (self, per cycle) | RECOVERY_CONDITION_PENDING |
                               RECOVERY_CONDITION_FAILED | VERIFIED_RECOVERY | INSUFFICIENT_EVIDENCE | ESCALATED
RECOVERY_CONDITION_PENDING   → MONITORING_RECOVERY | RECOVERY_CONDITION_FAILED | VERIFIED_RECOVERY | ESCALATED
RECOVERY_CONDITION_FAILED    → RECOVERY_FAILED | INCIDENT_REOPENED | ESCALATED
INSUFFICIENT_EVIDENCE        → AWAITING_REQUIRED_EVIDENCE | MONITORING_RECOVERY | ESCALATED
RECOVERY_FAILED              → INCIDENT_REOPENED | ESCALATED
INCIDENT_REOPENED            → CONTINGENCY_AWAITING_APPROVAL | ESCALATED | CANCELLED
CONTINGENCY_AWAITING_APPROVAL→ CONTINGENCY_IN_PROGRESS | ESCALATED | CANCELLED
CONTINGENCY_IN_PROGRESS      → AWAITING_REQUIRED_EVIDENCE | READY_FOR_MONITORING | ESCALATED | CANCELLED
VERIFIED_RECOVERY / ESCALATED / CANCELLED → (terminal)
```

## Role guards (defence in depth)
The Agent Action Gateway authorises the *action* that triggers a transition; the state machine adds a
second check on the triggering actor's role:

| Transition | Allowed roles |
| ALERT_TRIAGED → INTERVENTION_PROPOSED | system, agent (the agent proposes) |
| INTERVENTION_PROPOSED → INTERVENTION_RECORDED | supervisor, plant_admin (human accepts diagnosis) |
|---|---|
| DRAFTED → REVIEWED | supervisor, plant_admin |
| CONTINGENCY_AWAITING_APPROVAL → CONTINGENCY_IN_PROGRESS | supervisor, plant_admin |
| CONDITION_FAILED → RECOVERY_FAILED → INCIDENT_REOPENED → CONTINGENCY_AWAITING_APPROVAL | system, agent (automatic) |
| → VERIFIED_RECOVERY | system, agent (only after policy + quality release) |
| → CANCELLED | supervisor, plant_admin |
| → ESCALATED | system, agent, supervisor, plant_admin |
| (unlisted) | any authorised role |

## The cycle-17 branch (preserves history)
On verdict `violated`, `reopen_with_contingency`:
`MONITORING_RECOVERY → RECOVERY_CONDITION_FAILED → RECOVERY_FAILED → INCIDENT_REOPENED →
CONTINGENCY_AWAITING_APPROVAL`, marks contract V1 `violated` + `superseded_by` V2, creates the
bearing-replacement intervention (sequence 2), drafts V2, increments `reopened_count`, and publishes a
`recovery.reopened` outbox event. The first intervention and its evidence are never deleted.

## Guarantees (asserted by tests)
- Every transition writes a `STATE_TRANSITION` audit row with `prev_state` + `new_state`
  (`test_audit_completeness_and_knowledge_pending`).
- A model failure before a transition leaves state unchanged (`test_model_failure_preserves_state`).
- Recovery cannot reach `VERIFIED_RECOVERY` from a technician completion alone — quality release is
  required (`test_recovery_not_closed_by_completion_alone`, `test_quality_release_requires_quality_engineer`).
