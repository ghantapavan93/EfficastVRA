# Verified Recovery Agent — System Overview, in depth

> The single entry point for understanding the whole system — what it is, the full stack, the
> architecture, every feature, how it runs — **and an honest critique with a prioritized gap list.**
> Written to be read cold by another engineer or agent. Deep-dives live in the linked docs.

---

## 1. What it is (and the one idea)

An independent, **Efficast-aligned** manufacturing-AI prototype on **synthetic data** (not affiliated with
the real Efficast company; no real machine control). The thesis:

> **Work completed ≠ production recovered.**

A maintenance work order can be "done" while the line is still failing. This agent **defines what recovery
means** — a deterministic **Recovery Contract** — then **verifies it against post-intervention telemetry**,
keeps the incident open until the evidence holds, and **catches a false recovery** when the fault relapses.

**Hero scenario (Northstar Packaging, PO-2841):** fault **F27** on a CDX-220 conveyor drive looks fixed by a
coupling alignment; headline metrics read "recovered" — but a hidden bearing precursor climbs and **F27
relapses at cycle 17**. The system catches it, reopens, runs a bearing-replacement contingency, verifies 30
stable cycles + quality release, and only then closes.

---

## 2. The full stack (at a glance)

| Layer | Choices |
|---|---|
| **Backend** | Python ≥3.11 · FastAPI · uvicorn · SQLModel (SQLAlchemy 2 + Pydantic 2) · numpy |
| **Database** | SQLite (dev default, zero-config) ↔ Postgres + pgvector (prod path, `[postgres]` extra) — same schema, switch via `VRA_DATABASE_URL` |
| **RAG** | Deterministic 256-dim **lexical hash** embeddings (no ML model, no network); filter-then-rank retrieval |
| **Reasoning** | `DeterministicReasoningProvider` (default, no API key) ↔ optional `HostedReasoningProvider` (Anthropic Messages API via raw httpx; **narrative enrichment only**, silent fallback) |
| **Interop** | Self-contained **MCP** server (JSON-RPC 2.0 / stdio, 13 **read-only** tools); ISA-95 + Unified-Namespace (Sparkplug B) topic model; connector catalog |
| **Frontend** | TypeScript · Next.js 14 (App Router) · React 18 · Tailwind ("Forge" design system) · TanStack Query · Radix · framer-motion · lucide · cmdk |
| **Testing** | pytest (incl. AST **architecture fitness functions**, safety, MCP, RAG, e2e-API) · ruff · mypy · Vitest + Testing Library · Playwright |
| **Run** | `run.ps1` / `Makefile` (`install·dev·seed·reset·demo·eval·test`); backend :8000, frontend :3000; optional `docker compose` (pgvector + backend + frontend) |

Default dev path needs only **Python 3.11+ and Node 18+** — no Docker, no API key, no GPU. See
[`ARCHITECTURE.md`](ARCHITECTURE.md) for the C4 model and [`EVALUATION.md`](EVALUATION.md) for test counts.

---

## 3. Architecture — hexagonal, deterministic-by-default

Ports-and-adapters with a **composition root** ([`app/composition.py`](../backend/app/composition.py)) — "to
go to a real deployment you change only this module." Layered so the **domain core is pure**, the **agent
proposes**, and a **deterministic verifier + a single gateway decide and act**.

```
 MAIA alert ─▶ Agent (proposes) ─▶ Recovery Contract ─▶ Deterministic Evaluator (decides)
                     │                                          ▲
                     └──────── Agent Action Gateway ────────────┘   ← every side-effect, one choke point
                                  (RBAC · policy · human-approval · idempotency · circuit breaker · audit)
```

### The safety model — five invariants, each enforced (not just promised)

| # | Invariant | Enforced at |
|---|-----------|-------------|
| **a** | **No physical machine control** — ever | `gateway/actions.py` `PROHIBITED_ACTIONS` hard-denied at gateway entry; `EfficastPort` has no control method; `security.py` `PROHIBITED_PERMISSIONS`; **fitness test** fails the build if such a symbol is even *named* |
| **b** | **The LLM never decides closure** | `services/evaluator.py` is the sole verdict producer (no model call); `finalize()` closes only on `verdict=="verified"`; **fitness test** forbids `agent/`+`reasoning/` from importing the gateway |
| **c** | **Forecaster / decision / reliability layers are advisory** | pure-compute, read-only; never write state, grant approvals, or close; exposed only on read routes + read-only MCP |
| **d** | **MCP is read-only** | only read handlers registered; enforced by `tests/test_mcp.py` |
| **e** | **RBAC is server-authoritative** | role read from the resolved `User` row, never the client; gateway role check + state-machine transition guards; the **AGENT principal can propose/monitor/reopen but never approve, release quality, or close** |
| **f** | **The architecture is executable** | `tests/test_architecture.py` parses the import graph (pure core, no web in core, agent never actuates, tools only via gateway, no machine-control symbol) |

Deep-dives: [`SECURITY_MODEL.md`](SECURITY_MODEL.md), [`THREAT_MODEL.md`](THREAT_MODEL.md),
[`adr/`](adr/), [`GOVERNANCE.md`](GOVERNANCE.md).

---

## 4. End-to-end recovery flow

```
MAIA alert (F27) ─ triage ─▶ INTERVENTION_PROPOSED ─ human accept ─▶ INTERVENTION_RECORDED
   │ agent drafts Recovery Contract (perceive→retrieve→hypothesize→draft→self-critique→decide)
   ▼
DRAFTED ─ supervisor review ─▶ REVIEWED ─ evidence validated + approvals ─▶ READY_FOR_MONITORING
   │ start monitoring → Verification Window 1
   ▼
MONITORING_RECOVERY  ⟲ deterministic evaluate() every cycle
   ├ cycles 0–16: conditions PASSING (headline looks recovered; bearing precursor hidden-rising)
   ├ CYCLE 17: F27 recurs → verdict VIOLATED → reopen (history preserved)
   │     └▶ CONDITION_FAILED → FAILED → REOPENED → CONTINGENCY_AWAITING_APPROVAL
   │            ─ supervisor approves bearing job ─▶ IN_PROGRESS ─ complete ─▶ Window 2
   └ Window 2: 30 stable cycles + first-piece evidence + QUALITY_ENGINEER release
          └▶ finalize() [evaluate()=="verified"] ─▶ VERIFIED_RECOVERY ✅ (terminal)

Escape hatches: reopened_count ≥ 2 / approval rejected / window over max → ESCALATED;  supervisor → CANCELLED
```

The pivotal guarantee: between "alignment completed" and `VERIFIED_RECOVERY`, **only the deterministic
evaluator** can advance to closure, and the cycle-17 relapse is caught as a `NOT_RECUR` condition violation —
not by the LLM. Eval proof: `tests/test_agent_eval.py` ("never false-closes a relapse").

---

## 5. Feature catalog

**Core verification loop**
1. **Alert triage** — open MAIA alerts → one-click agent triage creates an incident.
2. **Agent diagnosis** — ranked root causes + proposed intervention + RAG citations; human accepts.
3. **Recovery Contract authoring & review** — structured conditions / evidence / approvals / policies; versioned.
4. **Evidence collection** — role-assigned requests with freshness + validity rules.
5. **Human approvals (HITL gates)** — incl. quality release & contingency.
6. **Verification monitoring** — start window, advance cycles, live per-cycle deterministic evaluation.
7. **Relapse handling & contingency** — F27-at-17 → reopen → contract v2 (bearing) → second window.
8. **Verified outcome** — before/after metrics, stable cycles, reopened count, quality-released.

**Agent intelligence**
9. **Inspectable reasoning trace** — perceive→…→reflect, with citations, confidence, model/prompt version.
10. **Grounded troubleshooting** — approved procedure + ranked causes + history + signals + lessons.
11. **Institutional knowledge loop** — agent proposes lessons; only a human curates (role-gated).

**Advisory analytics** *(never change state — see §7 for honesty caveats)*
12. **Recovery Forecaster** — early relapse warning from the bearing precursor + competing hypotheses.
13. **Decision Intelligence** — cost/production exposure, expected-cost-per-option, FMEA/RPN.
14. **Reliability statistics** — zero-failure demonstration test, **Wald SPRT**, bathtub-curve hazard, window grade.

**Interop, governance & ops**
14b. **Closure provenance & evidence trust** — the queryable "why was this decided & can we trust it?" record: deterministic conditions, evidence ranked by provenance tier (GRADE-style), human approvals, **proposed-vs-executed reconciliation**, and audit-chain integrity (advisory; independent of the LLM).
15. **Tamper-evident audit** + recompute/verify endpoint (hash-chained).
16. **Governance posture** — live control checks mapped to IEC 62443 / ISO 27001 / SOC 2 / NIST CSF / EU AI Act, with honest gaps.
17. **ISA-95 / UNS interoperability view** + machine-agnostic contract catalog + 5-connector reference catalog.
18. **Read-only MCP server** — external agents/Claude query verified mission/metrics/audit/forecast (13 tools).
19. **Notifications**, **real telemetry ingestion**, **health + SLI metrics**, **self-running demo**.

---

## 6. Code map (where things live)

**Backend** (`backend/app/`)
- `domain/` — 27 SQLModel tables, enums, the `RecoveryContractSpec` schema; `workflow/state_machine.py` (18 states, role-guarded transitions).
- `services/` — **`evaluator.py` (the only verdict producer)**, `cycle_engine.py`, `windows.py`, `evidence.py`, `quality.py`, `policy.py`, and the advisory `forecaster.py` / `decision.py` / `reliability_stats.py`, plus `troubleshooting.py`, `governance.py`, `knowledge.py`, `machine_profiles.py`, `telemetry.py`, `metrics.py`.
- `gateway/` — **the Agent Action Gateway** (`gateway.py` 12-stage pipeline; `actions.py` `PROHIBITED_ACTIONS`; `idempotency.py`; `circuit.py`); `tools/registry.py` (9 read + 6 write tools, importable only by the gateway).
- `agent/` + `reasoning/` — Reflexion-shaped plan-executor graph (`graph.py`), traces, deterministic + hosted providers.
- `workflow/` — `recovery_service.py` (orchestrator), `audit.py` (hash chain + transactional outbox), `reopening.py`, `demo.py`.
- `rag/`, `mcp_server.py`, `integration/` (isa95, connectors), `adapters/` (synthetic plant `ScenarioPhysics`, ports), `security.py`, `observability.py`, `composition.py`, `api/` (routes + serializers), `seed/`.

**Frontend** (`frontend/`)
- `app/(app)/` — pages: `missions`, `missions/[id]` (tabs: Overview, Agent Diagnosis, Agent Reasoning, Decision Intelligence, Recovery Confidence, Recovery Contract, Evidence, Verification Timeline, Contingency, Outcome), `alerts`, `inbox`, `troubleshoot`, `knowledge`, `system`.
- `components/` — `shell/` (nav rail, command bar + role switcher + pause, command palette), `mission/` (agent-reasoning, diagnosis-panel, decision-panel, reliability-panel, action-bar, contingency-compare), `contract/`, `evidence/`, `outcome/`, `timeline/` (verification-timeline + forecast-panel), `charts/` (hand-built SVG trajectory), `forge/` (the design system), `demo/`.
- `lib/` — `api.ts` (typed client, `X-VRA-User` header, ~40 endpoints), `hooks.ts` (TanStack Query, identity-keyed, `useRecoveryActions`), `role.tsx`, `types.ts`, `state-meta.ts`, `utils`, `announce`.
- **Data flow:** component → hook → `api` → FastAPI (the `/api` rewrite proxy avoids CORS in dev). The frontend renders backend truth and **never decides recovery**.

---

## 7. Critique & gap analysis (honest)

A skeptical senior-staff review of the *current* code. The disclosed prototype caveats
([`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md): SQLite, header auth, polling, lexical RAG, synthetic
physics) are **not** re-listed here — these are issues those docs *don't* surface. Severity = "what would
matter if someone took this to production." Each item has `file:line` evidence.

> **Status (latest commit): H1, H2–H6, H7, and M1 are addressed.** The gateway now resolves a failed
> proposal to `failed` and the docstring is accurate (H1); the SPRT, forecaster, FMEA delta, and the
> renamed **"recovery progress"** (was "outcome confidence") now carry explicit *design-point / heuristic
> / illustrative* basis notes in code, API, and UI (H2–H6); `keep_monitoring` charges scrap-until-detection
> for a consistent cost model (H5); the safety suite gained an **allowlist invariant** (every tool in a safe
> class, every write gated) + a **no-stuck-proposal** invariant + an unexpected-error test (H7); and reopen
> derives the recurrence key from the `fault_*` convention instead of the literal `fault_f27` (M1).
>
> **Update 2 (provenance build):** H1 now also wraps the tool handler in a **savepoint** (`begin_nested`)
> so a handler's partial writes roll back atomically; H8 added a DB **`UNIQUE(correlation_id, seq)`** on
> the audit log (a concurrent seq collision fails loudly instead of silently forking the hash chain); and
> a new **Provenance & Evidence-Trust layer** ([`PROVENANCE.md`](PROVENANCE.md)) adds GRADE-style
> evidence tiering + a closure-provenance record with **proposed-vs-executed reconciliation** ("logs alone
> are not proof") — the runtime answer to "why decided this / can we trust the closure?".
>
> **Update 3 (hardening):** **M6** added a frontend error boundary (`error.tsx` + `global-error.tsx`) and
> a guarded empty-body parse (no more white-screen); **M9** proved outbox head-of-line non-blocking (a
> poison event no longer starves a healthy one) + a stable sort tie-break; **M10** the tamper badge no
> longer reads "verified" on an empty chain, and tests now prove the audit chain detects **deletion and
> reorder** (not just a field edit); **M8** replaced assert-anything tests with real invariants (risk-scaled
> decision argmin, pinned SPRT values); and a forecaster `lead_cycles` off-by-one (truthiness at cycle 0)
> is fixed.
>
> **Update 4 (second, deeper adversarial pass — verified the fixes + found new gaps):** a fresh review
> independently confirmed H1/H7/H8 hold, then found gaps the first pass missed. **Fixed:** *cross-fault
> blindness* (`is_stable_observation` now treats **any** fault as non-stable, so "stable" means genuinely
> fault-free — the prior pass demonstrated a metric-nominal relapse could false-close); the contract
> builder now **refuses a spec that doesn't test the originating fault's non-recurrence** (a vacuous
> contract was demonstrably a false-closure path); the generic **`/api/tools/{name}` endpoint** (it
> raised NameError → 500 on every call) now works; the **audit hash now signs the attribution fields**
> (incident/contract/plant/model/prompt version) so a verdict can't be silently re-attributed; two
> provenance **false positives** fixed (pending evidence is discounted not zeroed; in-flight proposals are
> only a discrepancy at closure); the agent "recovery confidence" / "diagnostic confidence" are now
> labelled **heuristic** (residual H4); reconciliation re-scoped to "internal consistency, not proof of
> authorization" (H-C); + small robustness polish and a dead-code removal.
>
> Still open (honestly deferred): **C2** stale-evidence TOCTOU (re-check freshness at closure — matters
> once the wall-clock scheduler exists); **M-A** quality gate fail-open when a contract omits the
> first-piece condition; **M-B** the live window length is hardcoded 30 vs. the contract spec; **M-C**
> the knowledge-candidate text is hardcoded F27/BR-6205; plus **M2/M4**, assorted **LOW**, and the
> **MISSING** infra (real authn/multi-tenancy, durable scheduler + outbox worker, telemetry provenance,
> semantic-embedding RAG) — the items needing a Postgres/broker environment to build *and verify*
> honestly. Findings are kept as the record.
>
> **Update 5 (third audit pass — Phase 33, two deep agents: frontend + backend).** Fixed: **M‑A** (quality
> gate now fails closed and requires a `PASSED` quality condition, generalised off the `first_piece`
> literal); **M‑B** (window opened from the contract spec, floored at 10); **M3** (RAG conflict dedup keyed
> on document/revision/section); **M4** (troubleshoot UI badge tones from real approval status + softened
> claim); **N1** (approval `decision` is validated — no more silent coercion to REJECT); **N2** (Decision
> Intelligence flags `indicative` when there's no live forecast, so the dollar figures aren't read as
> calibrated); **N4** (provenance `trustworthy` weighs only the *validated* evidence, so a superseded first
> attempt no longer marks a good closure untrustworthy); plus frontend: the **OutcomePanel partial‑data
> crash**, the **`.glass` opaque fallback** (older engines no longer render transparent chrome), faint‑label
> contrast, the progress bar's verified tone gated on real closure, and machine‑agnostic outcome/a11y
> labels. Still deferred: **M‑C**, **C2**, the inventory‑reservation‑outside‑gateway (exploit closed), and
> the infra batch.
>
> **Update 6 (Phase 34 — the two deferred MEDIUMs closed).** **C2** is fixed: the evaluator computes its
> verdict `as_of` a moment (default *now*) and re‑checks evidence freshness at *use* time, so evidence that
> was fresh at submission but has since aged past its `freshness_max_s` budget no longer satisfies its
> condition at closure (`services/evidence.py:is_fresh_at`, `services/evaluator.py`; the monitoring/reasoning
> paths that pass no `as_of` are unchanged). **M‑C** is fixed: the knowledge candidate's text is now
> *derived from the incident* — fault, machine model, failed‑vs‑held interventions, the replaced component
> (+ part number), the relapse cycle read from the first faulted observation, and the verified window — via
> `tools/registry.py:derive_knowledge_candidate`, replacing the hardcoded F27/CDX‑220/BR‑6205 string (the
> relapse cycle is now the real `17`, not a rounded "~20"). Tests: `test_freshness_at_closure.py` (3) +
> `test_knowledge.py` (2, incl. a mutation proof the lesson tracks a different machine/part). Backend
> **107** / frontend **24** green; hero demo still reaches VERIFIED_RECOVERY. Now deferred: only the
> inventory‑reservation‑outside‑gateway (exploit closed) and the infra batch (needs Postgres/broker).

### HIGH — correctness or claim-integrity
- **H1 — Gateway doesn't roll back its own flushed rows on an unexpected exception.** `gateway/gateway.py` flushes `ActionProposal` + audit rows, then re-raises without rollback; "clean rollback" is left to the caller and is never exercised by a test. `RecoveryService.advance()` calls the gateway mid-loop after already transitioning state. *Fix: own a savepoint and roll back to it before re-raising.*
- **H2/H3/H4/H6 — the "depth" analytics speak the vocabulary of calibrated inference but are demo-fitted/heuristic.** The **SPRT** `p1=0.20` is explicitly tuned so accept falls after cycle 17 (`reliability_stats.py`); the **Forecaster** `p_relapse` is a linear transform of a *planted* `bearing_precursor` channel (`forecaster.py` + `adapters/synthetic.py`) — a read-back, not a prediction; the **"outcome confidence %"** is a `40 + 55·streak/required` ramp rendered as a probability (`serializers.py` → mission card/status strip); the **FMEA "without-agent" RPN** delta is a hardcoded constant presented as a measured benefit. *Fix: relabel each as an illustrative/design-point assumption (the project already does this for cost figures — extend it to these).*
- **H7 — Safety claims are proven by denylists/existence checks, not invariants.** `test_safety.py` / `test_architecture.py` use substring blocklists + a fixed forbidden-name list; a new `/api/actuate` route or a direct `Incident` mutation bypassing the gateway would pass green. *Fix: invert to allowlists — assert every write tool's `action_class` is in an allowed set and that every write-classed proposal ends `executed/failed`.*
- **H8 — Zero concurrency tests; idempotency + audit-seq are check-then-insert with no lock.** Masked by SQLite's single writer, but the Postgres prod path has real concurrency: two same-key requests can both pass `lookup()`, two audits on one correlation-id can collide on `seq`. *Fix: rely on the PK insert (catch IntegrityError), add `UNIQUE(correlation_id, seq)`, add a 2-thread race test.*

### MEDIUM — robustness & "machine-agnostic" leakage
- **M1 — `policy.should_reopen` hardcodes `"fault_f27"`** — contradicts the machine-agnostic claim; derive the recurrence key from the contract's `NOT_RECUR` condition / `incident.fault_code`.
- **M2 — Timeline thresholds/baselines are hardcoded in the frontend** (`verification-timeline.tsx`), not contract-derived — won't track any other machine.
- **M3 — RAG conflict-dedup keys on a text hash**, so an obsolete revision that repeats a sentence verbatim is silently dropped — hiding the very conflict it should surface. Dedup on `(document_id, revision, section)`.
- **M4 — `troubleshoot` claims "every line approval-checked & fresh"**, but `history`/`what_worked` are ungated and `what_worked = history[0]` trusts an unordered query; the UI badges every procedure green regardless of real status.
- **M5 — Invalid `decision` string silently becomes REJECT** (`knowledge.py`), burning the one-shot review. Validate `decision ∈ {approve, reject}` → 422.
- **M6 — No frontend error boundary** — a malformed payload or a `res.json()` on an empty 200 white-screens the app. Add `error.tsx` + `global-error.tsx`.
- **M7 — Polling UI has no staleness/offline signal** — *FIXED (Phase 31):* a live **Live / Stale / Offline** connection indicator now renders in the command bar (driven by `dataUpdatedAt` + `navigator.onLine`), so a frozen screen no longer reads as live.
- **M8/M9/M10 — tests assert too little:** a "flip" test that accepts any option; an outbox dead-letter test that never proves head-of-line non-blocking; a tamper badge that reads "verified" on an **empty** chain (`count: 0` ⇒ `ok: true`) and tests that only mutate a field (never delete/reorder rows).

### MISSING for a real deployment (beyond disclosed caveats)
- **Real authn & multi-tenancy** — absent `X-VRA-User` defaults to the **supervisor** principal (anonymous = privileged); single global tenant; demo reset wipes the whole DB. Needs OIDC/JWT + per-tenant isolation.
- **Wall-clock windows / durable scheduler** — windows advance only via an explicit "advance N" action; no timer, no crash recovery (despite "Temporal-compatible" framing).
- **Durable outbox worker** — the relay runs inside request middleware; a crash between commit and the next request leaves events stuck with nothing draining them, so "exactly-once published decision" doesn't fully hold.
- **Model lifecycle** — hosted provider untested against a live endpoint; no eval gate on upgrades, no cost/latency budget, no prompt pinning beyond a string.
- **Telemetry provenance** — every observation is hardcoded `source="SyntheticEfficastPort"`, `freshness_s=2` even for ingested data; no signed provenance, no clock-skew handling.
- **Durable observability** — in-memory metrics (lost on restart); no tracing/log-shipping/alerting despite the IR runbook.

### LOW
Client-only role gating reads as enforcement (backend is authoritative, but `localStorage` role toggles privileged buttons); approval dialog closes before the async result; some `GatewayError`/`ApiError.detail` swallowed in demo/triage; forecaster `lead_cycles` truthiness bug at `cycle_index==0`; color cliffs at exactly `p_relapse ≥ 0.6`; frontend tests are render-only (no error/empty/denied cases).

### What's genuinely solid
The **deterministic evaluator is the real source of truth** and is honestly separated from the LLM; "verified"
correctly requires `technical_pass AND quality_release` and treats recurrence as VIOLATED regardless of streak;
**agent self-approval is provably blocked**; the **hash-chained audit** is sound for field mutation; the
**hexagonal boundaries are enforced by AST fitness functions** (rare rigor); division-by-zero is guarded in the
analytics. **Net:** the *core thesis* — deterministic, human-gated, audited verification of recovery — is
well-executed and honest. The risk concentrates in the **statistical/predictive "depth" layers**, which dress
hand-tuned or hardcoded numbers in the language of calibrated inference, and in **safety tests that assert
existence rather than invariants**. Closing H1, the H2–H6 relabels, H7, and H8 would align what it *proves*
with what it *claims*.
