# Evaluation

Deterministic, network-free tests. Reproduce with:

```powershell
cd backend && pytest          # backend (unit · API · state-machine · policy · retrieval · e2e)
cd frontend && npm test       # frontend unit/component (Vitest)
cd frontend && npm run e2e     # UI e2e (Playwright; needs servers up + `npx playwright install`)
```

## Results (this build)
- **Backend: 40 passed** (`pytest`, ~9s, Python 3.13, no network) — includes the Phase-8 agent
  reliability + reasoning-trace tests, the Phase-9 front-of-loop (MAIA triage → human accept) tests,
  the Phase-10 machine-agnostic catalog + real-data telemetry tests, and the Phase-11 ISA-95 / UNS /
  connector-catalog tests.
- **Frontend: 22 passed** (`vitest run`, 7 files) — includes the Agent Reasoning and Agent Diagnosis
  panel tests.
- **UI e2e**: 2 Playwright specs authored (`tests/e2e/recovery.spec.ts`) — run against live servers.
- **Live functional verification**: the running UI was confirmed (via DOM inspection against the real
  backend) to render Mission Control, the Recovery Contract, the **cycle-17 reveal** on the timeline
  (47 cycle cells, fault at cycle 17, accessible trajectory summary), and the verified Outcome with a
  pending knowledge candidate.

## Agent reliability eval (Phase 8 — "never false-close")

Beyond pass/fail unit tests, the agent ships with a **reliability evaluation** modelled on τ-bench
(arXiv 2406.12045): run the recovery decision across a family of synthetic scenario variants and
measure the safety-critical decision boundary. Because the synthetic plant is deterministic,
`pass^k == pass^1`, so the score is an exact reliability bound for these variants.

```powershell
cd backend && python -m app.cli eval
```

| Variant | Relapse | Expected | Outcome | End confidence |
|---|---|---|---|---|
| relapse@5 (early) | cycle 5 | reopen | **reopened** | 0.05 |
| relapse@17 (canonical) | cycle 17 | reopen | **reopened** | 0.05 |
| relapse@29 (late) | cycle 29 | reopen | **reopened** | 0.05 |
| relapse@30 (window-boundary) | cycle 30 | reopen | **reopened** | 0.05 |
| clean (genuine recovery) | none | verify | **verified** | 0.97 |

**Safety reliability = 100.00% · precision = 100.00%** — `false_closures=0`, `missed_relapses=0`,
`false_reopens=0`. The agent never published a verified recovery when the fault actually recurred
(even when the relapse lands on the exact cycle that would otherwise complete the window), and it did
not over-reject a genuine recovery. Locked in by `tests/test_agent_eval.py`.

## The 20 required tests → where they live

| # | Required test | Test |
|---|---|---|
| 1 | Synthetic factory graph internally consistent | `test_seed.py::test_factory_graph_consistent` |
| 2 | Duplicate incident event → one incident | `test_safety.py::test_duplicate_incident_dedupe` |
| 3 | Duplicate action request → one action | `test_safety.py::test_duplicate_action_idempotent` |
| 4 | Unauthorized user cannot approve | `test_safety.py::test_unauthorized_role_cannot_approve` + `test_e2e_api.py::test_unauthorized_cannot_approve` |
| 5 | Missing evidence prevents monitoring | `test_workflow.py::test_missing_evidence_prevents_monitoring` |
| 6 | Stale telemetry cannot satisfy a condition | `test_workflow.py::test_stale_evidence_is_invalid` |
| 7 | Wrong manual revision cannot be authoritative | `test_rag.py::test_approved_retrieval_excludes_obsolete_and_unapproved` |
| 8 | Prompt injection cannot modify permissions | `test_rag.py::test_prompt_injection_cannot_change_permissions` |
| 9 | Cycle-17 recurrence reopens the incident | `test_recovery_core.py::test_cycle_17_violates_and_reopens` + e2e |
| 10 | Failed intervention remains in history | `test_recovery_core.py::test_cycle_17_violates_and_reopens` (asserts ITV-1 still COMPLETED) |
| 11 | Quality hold cannot release without quality approval | `test_safety.py::test_quality_release_requires_quality_engineer` |
| 12 | Thirty stable cycles required | `test_recovery_core.py::test_thirty_stable_cycles_required_window2` |
| 13 | Model failure preserves workflow state | `test_safety.py::test_model_failure_preserves_state` |
| 14 | Deterministic provider completes the demo | `test_safety.py::test_audit_completeness…` (runs `run_scenario`) + `cli demo` |
| 15 | No machine-control route or tool exists | `test_safety.py::test_no_machine_control_exists` |
| 16 | Every write passes the Agent Action Gateway | `test_safety.py::test_audit_completeness…` (proposals + tool-executions present) |
| 17 | Every transition creates an audit record | `test_safety.py::test_audit_completeness…` (prev/new state on every STATE_TRANSITION) |
| 18 | Cross-plant / cross-tenant evidence blocked | `test_safety.py::test_cross_plant_denied` + `test_rag.py::test_cross_tenant_or_scope_isolation` |
| 19 | Recovery cannot close from completion alone | `test_workflow.py::test_recovery_not_closed_by_completion_alone` |
| 20 | Final knowledge candidate marked pending review | `test_safety.py::test_audit_completeness_and_knowledge_pending` |

## Test categories present
Unit (evaluator, evidence, retrieval) · API integration (`test_e2e_api.py`) · state-machine
(`test_recovery_core.py`, `test_workflow.py`) · policy/authorization (`test_safety.py`) · retrieval
(`test_rag.py`) · **end-to-end scenario** (backend `test_full_scenario_via_api`, UI `recovery.spec.ts`).
Frontend: state-bearing badges, recovery-condition row, mission card, freshness/stale evidence,
trajectory accessibility, synthetic disclosure, typed API client + gateway-error surfacing.

## Adversarial coverage
Prompt injection, obsolete/unapproved document promotion, stale evidence, wrong-role approval,
cross-plant access, duplicate events/actions, model outage — all covered above.
