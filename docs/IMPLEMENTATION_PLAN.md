# Implementation Plan

Single source of truth for *what is done* and *what the current phase is*. Detail lives in the linked
docs; this is the index + the active phase. (Established 2026‑06‑24; prior phases reconstructed from the
git history and `docs/`.)

## Completed (built + tested; see git log + docs)
- **Core loop** — Recovery Contract primitive, 18‑state durable machine, deterministic evaluator, cycle
  engine, Agent Action Gateway (no machine control), tamper‑evident hash‑chained audit, transactional
  outbox. Hero scenario: F27 relapse at cycle 17 → reopen → bearing contingency → verified.
- **Agent & RAG** — bounded Reflexion‑style reasoning graph (deterministic provider; optional hosted),
  inspectable traces, approval‑filtered NumPy RAG, reliability eval ("never false‑close").
- **Front of loop** — MAIA‑style alert → agent triage → human accept.
- **Machine‑agnostic** profiles + real‑data telemetry seam; **ISA‑95/UNS** + connector catalog;
  read‑only **MCP** server (15 tools).
- **Advisory analytics** — Recovery Forecaster, Decision Intelligence (economics + FMEA), Reliability
  statistics (zero‑failure demo test + Wald SPRT + bathtub hazard), counterfactual contract calibration.
- **Governance/ops** — IAM/RBAC, observability/SLI, governance posture, incident‑response docs.
- **Knowledge learning loop**, **Troubleshooting**, **Provenance & evidence‑trust** (reconciliation).
- **Two critique passes** (`docs/SYSTEM_OVERVIEW.md` §7) + fixes: H1–H8, M1/M6/M8/M9/M10, cross‑fault
  blindness (C1/H‑A), contract‑binding guard, audit attribution signing, `/api/tools` repair, etc.
- **Efficast positioning** — `docs/EFFICAST_FIT.md`, `docs/EFFICAST_INTEGRATION_SPEC.md` (read‑only
  consume + publish‑verdict‑back; auth "to be agreed"); consumption seam.
- **Futuristic frontend pass** + M7 live/stale/offline connection indicator.

**Baseline:** backend **165 pytest** passing · frontend **24 vitest** passing · typecheck/lint/build clean.

**Phase 36 — Recovery Assurance R&D (in progress).** Four web-grounded research tracks (novelty/category,
causal-consistency model, contract DSL+FSM, evaluation/data/verdict) → [`CAUSAL_RECOVERY_RESEARCH.md`](CAUSAL_RECOVERY_RESEARCH.md)
(verdict: **GO, conditional**; rename Fingerprint→**Expected Recovery Signature**; drop "causal" from the
headline until matched-conditions exists; moat winners = False-Closure Risk Score + Intervention
Effectiveness). **36a shipped:** `services/recovery_signature.py` `score_signature()` — an advisory,
read-only intervention-consistency layer whose Expected Recovery Signature is *derived from the contract's
own conditions* (machine-agnostic) and which scores the hero's two headline-identical windows **oppositely**
(coupling → RECOVERY_OBSERVED; bearing → STRONGLY_CONSISTENT, conditions-unverified). Tests:
`test_recovery_signature.py` (6). **36b shipped:** read-only `/api/incidents/{id}/signature` route +
`signature_view` serializer + a **Recovery Signature** mission tab/card (`recovery-signature-panel.tsx`)
showing the rung, alignment, per-signal expected-vs-actual bars, and the honesty caps — verified live in the
browser (Strongly consistent · +1.00 on the hero). **36c shipped:** a deterministic Monte-Carlo
**calibration harness** (`services/calibration.py`) — refactored the scorer to a pure `score_observations`
core (graded precursor) reused by the harness, generates seeded genuine-vs-latent-relapse scenarios, and
reports **Brier (+ decomposition), ROC-AUC, reliability curve, early-warning rate** (read-only route
`/api/calibration`). Surfaced as an **award-grade animated reliability-diagram card** on /system
(`components/system/calibration-panel.tsx`) — verified live (Brier ≈0.14, AUC ≈0.99, honest mid-range
over-confidence shown). Tests: `test_calibration.py` (3). **36d shipped — the third primitive, Recovery
Certificate:** `services/certificate.py` composes (read-only) the deterministic verdict + closure
provenance + intervention-consistency signature + a tamper-evident audit-seal hash into an exportable
**Return-to-Service Certificate** (route `/api/incidents/{id}/certificate`), surfaced as an award-grade,
**printable** mission tab (`components/outcome/recovery-certificate.tsx`: embossed seal, conditions
checklist, trust-weighted evidence, human signatures, audit/cert hashes, print-isolation CSS) — verified
live (Certified · trustworthy · alignment 1.00 on the hero). Completes the trio **Contract → Signature →
Certificate**. Tests: `test_certificate.py` (3). **39 shipped — False-Closure Risk Score (moat #1):**
`services/false_closure_risk.py` — an explainable, advisory, read-only estimate of the risk that closing
*now* would be a false closure, composed from the intervention-consistency signature + relapse precursor +
stable-cycle margin + weakest validated evidence (each factor's contribution shown; a recurring fault forces
high). Route `/api/incidents/{id}/closure-risk`; surfaced as an animated **radial risk gauge** with
per-factor bars (`components/mission/closure-risk-panel.tsx`) — verified live (6% · Low on the verified
hero). Tests: `test_false_closure_risk.py` (3). The full advisory vertical is now live: Contract →
Signature → Calibration → Certificate → Closure-Risk.

**40 shipped — Recovery Disposition (the four-outcome decision, made explicit) + integrity fixes** (from an
external product review mapped to code): `services/disposition.py` classifies an incident's current truth as
VERIFIED / CONDITIONAL / FAILED / INSUFFICIENT_EVIDENCE / ESCALATION_REQUIRED (else IN_PROGRESS), and exposes
(a) the **hard closure invariants** as a pass/fail checklist — `can_close` = the evaluator's verdict, which a
low risk score can never override; and (b) the **technician↔telemetry↔quality status matrix** → recommends
escalation on disagreement instead of forcing a winner (supervisor-intent flagged as an honest gap). Route
`/api/incidents/{id}/disposition`; UI `components/mission/disposition-panel.tsx`. Read-only; the evaluator
still owns closure. Also fixed a real applicability bug: `rag/retrieval.py` now enforces **effective_date**
(a future-dated procedure is no longer retrieved before it is effective). Tests: `test_disposition.py` (4),
`test_retrieval_effective_date.py` (1). Confirmed already-present (review surfaced, code verifies): the
causal-confidence ladder w/ honesty caps (`recovery_signature.py`), intervention "fingerprints"
(`expected_signature`), contract versioning (`superseded_by`), evidence provenance + freshness-at-closure.
Genuinely deferred: Recovery-Debt/Conditional persistence, structured V1→V2 change-delta, supervisor-intent
capture, knowledge-candidate revisioning. Next: 37 generative-physics data + fleet; 38 adversarial golden suite.

**41 shipped — Comparable-Conditions Gate (the causal-honesty backbone) + parallel research program.**
Driven by a principal-level program request, run as: (a) a parallel research **workflow** (3 read-only
agents → synthesis) on competitors, comparable-conditions methods, and return-to-service standards; (b) deep
implementation of the #1 new primitive. **Gate:** `services/comparable_conditions.py` compares the plant's
normal operating context against the verification window's context across 8 dimensions (product, mode, load,
sensor health, speed = key; ambient = minor; lot, shift = info) → COMPARABLE / PARTIALLY_COMPARABLE /
NOT_COMPARABLE / UNKNOWN with a per-dimension breakdown + confidence multiplier; **default-deny** (missing
context → UNKNOWN, never silently comparable). Window gains `baseline_context` + `observed_context` (JSON;
`windows.DEFAULT_OPERATING_CONTEXT`). Wired into the **disposition**: NOT_COMPARABLE + machine-recovered →
INSUFFICIENT_EVIDENCE (confound risk). Route `/api/incidents/{id}/comparability`; UI
`components/mission/comparable-conditions-panel.tsx`. Read-only; the evaluator still owns closure. Also
fixed `effective_date` enforcement in RAG (Phase 40). Tests: `test_comparable_conditions.py` (6). Research
docs written: `COMPETITOR_AUDIT.md`, `CATEGORY_DEFINITION.md` (category = **Post-Intervention Production
Requalification**; standards: nuclear PMT, pharma IQ/OQ/PQ+CPV, aviation RTS/CRS, ISO CAPA), `NOVELTY_CLAIMS.md`
(3 defensible claims; 9 overclaims to remove). **Deferred next (research-prioritized):** upgrade the gate to
SMD + baseline-band + CUSUM; cap the signature ladder via the gate (min() ceiling); Recovery-Debt/Conditional
persistence; emit context per-cycle from the generator.

**42 shipped — Comparable-Conditions as a system-wide decision invariant (rule `ccr-1.0`).** One canonical
policy, `services/recovery_policy.py::derive_effective_recovery_confidence(raw, comparability, multiplier,
evidence_status)` → it can only LOWER confidence, never raise it, and never overrides a hard requirement.
COMPARABLE = normal; PARTIALLY = reduced + confounders exposed + strong causal language withheld;
NOT_COMPARABLE/UNKNOWN = forced INSUFFICIENT_EVIDENCE (UNKNOWN is default-deny); FAILED relapse and missing
quality/evidence/freshness gates dominate regardless of comparability. Applied to: signature ladder (caps the
rung, retires the hardcoded `conditions_matched=UNKNOWN`), disposition (policy-driven `can_close`),
**finalize closure gate** (a non-comparable recovery cannot reach VERIFIED_RECOVERY → INSUFFICIENT_EVIDENCE,
and **no knowledge candidate** is created), certificate (status `not_certified` when blocked), false-closure
risk (new comparability factor), and the frontend badges. Provenance recorded (raw / classification /
multiplier / effective / confounders / policy_result / rule_version) on the verified + insufficient audit
events and in every API payload; new audit type `RECOVERY_INSUFFICIENT`. Tests: `test_recovery_policy.py`
(14) — incl. raw 0.99 + NOT_COMPARABLE/UNKNOWN → INSUFFICIENT, PARTIALLY reduces, COMPARABLE normal, relapse
stays FAILED, missing quality/stale still block, no surface shows VERIFIED when effective = INSUFFICIENT, KC
blocked unless comparable. Docs hardened with citations + confidence legend (COMPETITOR_AUDIT /
CATEGORY_DEFINITION / NOVELTY_CLAIMS). Next (research-prioritized): upgrade gate internals to SMD/CUSUM;
**Recovery Debt / Conditional** (separate phase); per-cycle context emission.

**43 shipped — Recovery Debt (the CONDITIONAL outcome, made real).** A persisted, time-boxed *concession /
deviation permit* (`domain/models.py::RecoveryDebt`, `RecoveryDebtStatus`): production may continue under
explicit restrictions while a **waivable** condition is deferred, so a CONDITIONAL recovery can never
silently become a permanent closure. **Granted only by an authorised human through the Agent Action
Gateway** (`grant_recovery_debt`, ActionClass.APPROVAL_REQUIRED, `requires_human`, roles supervisor/quality/
plant-admin) with a policy gate that **never lets a relapse (NOT_RECUR), a quality condition, or anything
safety-bearing be waived** (`services/recovery_debt.py::unwaivable_reason`). Lifecycle: ACTIVE → **SETTLED**
(the waived condition later verifies, deterministic) or **BREACHED** at expiry → **auto-escalation** (state
→ ESCALATED). Disposition integration: an active waiver ⇒ **CONDITIONAL** (`can_close` False); a breached
waiver ⇒ ESCALATION_REQUIRED. Routes `/recovery-debt` (GET) + `/grant` (gateway) + `/settle` + `/sweep`;
audit types RECOVERY_DEBT_GRANTED/SETTLED/BREACHED. UI: `components/mission/recovery-debt-panel.tsx` (view +
role-gated grant form + settle) — verified live (ACTIVE waiver on a monitoring incident → CONDITIONAL, 0
console errors). Tests: `test_recovery_debt.py` (6 — gateway role/human gate, non-waivable denial, settle,
breach→escalate, active-debt-blocks-VERIFIED). Frozen architecture intact (every write through the gateway;
deterministic evaluator still owns the hard verdict). Next: upgrade comparability internals to SMD/CUSUM;
per-cycle operating-context emission; A2 profile-driven reopen/contingency.

**Deployment readiness (Render + Vercel + Neon, all free):** the repo deploys by *configuration, not code*
— `main.py` lifespan creates tables + seeds on first boot; `/health` exists; `db.py` normalizes a
`postgres(ql)://` URL to psycopg3 and enables `pool_pre_ping`/`pool_recycle` for Neon scale-to-zero;
`config.py` also accepts `DATABASE_URL`; the frontend already reads `BACKEND_URL` from env. Ship files:
`render.yaml`, `backend/.python-version`, `docs/DEPLOYMENT.md` (step-by-step). The `psycopg[binary]`
driver is the existing `[postgres]` extra. Local SQLite dev/tests unchanged.

## Current phase — Phase 32: Discovery Q&A (evidence‑backed)
**Goal:** answer the 12 founder/judge discovery questions in depth, each grounded in actual code + a test,
with Efficast‑internal questions honestly tagged INFERRED/UNKNOWN (not asserted). No code redesign.

**Acceptance criteria:**
- [x] All 12 questions answered in `docs/DISCOVERY_QA.md`, each with a verdict + `file:line`/test evidence
      for capability claims, and a confidence tag for Efficast‑internal questions.
- [x] No claim exceeds what the code proves; Efficast‑internal unknowns recorded in `docs/RESEARCH_GAPS.md`.
- [x] Test baseline still green (101 / 22) — no behavior changed this phase.

**Status: COMPLETE** (2026‑06‑24). Deliverable: [`DISCOVERY_QA.md`](DISCOVERY_QA.md).

## Current phase — Phase 33: Deeper backend+frontend audit + fix MEDIUM gaps
**Goal:** a third, deeper adversarial pass (frontend especially — under‑audited, and the new glass/glow
pass risks contrast/robustness regressions) to find NEW gaps, then solve the high‑value + known‑open
MEDIUMs (M‑A quality fail‑open, M‑B contract‑driven window, M3 RAG dedup, M‑C knowledge‑candidate
hardcoding), each as a small tested unit. Preserve the hero scenario reaching VERIFIED_RECOVERY.

**Acceptance criteria:**
- [x] Two deep‑audit agents (frontend + backend) ran; new gaps triaged into fix / defer.
- [x] **Fixed:** N1 (approval decision validated — no silent REJECT), M‑A (quality gate fail‑closed +
      PASSED, generalised off `first_piece`), M‑B (window opened from contract spec, floored at 10),
      M3 (RAG conflict dedup on doc/revision/section), N2 (decision flags `indicative` when no live
      forecast), N4 (provenance trust weighs only validated evidence), + frontend: OutcomePanel
      partial‑data crash guard, `.glass` opaque fallback, faint‑label contrast, progress‑bar verified‑tone
      gated on actual closure, troubleshoot badge tone + softened claim, machine‑agnostic outcome/a11y labels,
      `error.tsx` docstring honesty.
- [x] Tests: N1 schema test + frontend OutcomePanel partial‑data + api empty‑body added; full‑scenario
      regression proves the demo still verifies under M‑A/M‑B. Backend **102** / frontend **24** green;
      typecheck/lint/build clean; loop verified live (VERIFIED_RECOVERY).
- **Deferred (with reason):** M‑C (knowledge‑candidate hardcoding — medium, demo unaffected), C2 (stale‑
      evidence TOCTOU — needs the wall‑clock scheduler to matter), N3/N5 (debatable/cosmetic), N6 (inventory
      reservation outside gateway — exploit closed by the state guard; architectural), N7–N9 (low/cosmetic),
      deeper frontend a11y (`text-faint` token, focus ring over glass).

**Status: COMPLETE** (2026‑06‑24).

## Current phase — Phase 34: close the deferred MEDIUMs (C2 + M‑C)
**Goal:** finish the two deferred MEDIUM gaps as small tested units — locally verifiable, no new infra —
preserving the hero scenario reaching VERIFIED_RECOVERY. (The infra batch — real authn/multi‑tenancy,
durable scheduler + outbox worker, semantic‑embedding RAG — stays deferred: it needs a Postgres/broker
environment to build *and verify* honestly, and building it on SQLite would mean claiming durability we
can't prove.)

**Acceptance criteria:**
- [x] **C2 — evidence freshness re‑checked at closure (not only at submission).** The evaluator now
      computes its verdict `as_of` a moment (default *now*) and evidence that was fresh when submitted but
      has since aged past its `freshness_max_s` budget no longer satisfies its condition. New
      `evidence.is_fresh_at()`; `requirement_satisfied`/`latest_valid_item` take an opt‑in `as_of`
      (monitoring/reasoning paths that pass none are unchanged). `evaluator.evaluate(..., as_of=)` threads
      it to the QUALITY condition. Locus: `services/evidence.py`, `services/evaluator.py`.
- [x] **M‑C — knowledge candidate derived from the incident, not hardcoded.** `tools/registry.py`
      `derive_knowledge_candidate()` builds the title/lesson/component/models/conditions from the fault,
      machine model, failed‑vs‑held interventions, replaced component (+ part number), the relapse cycle
      (read from the first faulted observation), and the verified window — replacing the literal
      F27/CDX‑220/BR‑6205 text. Generalises to any machine/fault; the relapse cycle is now the real `17`
      (was a rounded "~20").
- [x] Tests: `tests/test_freshness_at_closure.py` (3 — unit `is_fresh_at`, evaluator stale‑at‑closure
      blocks closure, opt‑in backward‑compat) + `tests/test_knowledge.py` (2 — derived‑from‑rows, and a
      mutation proof that the lesson tracks a *different* machine/part while the old literals disappear).
      Backend **107** / frontend **24** green; hero demo verified live (VERIFIED_RECOVERY, derived
      candidate PENDING_REVIEW).

**Status: COMPLETE** (2026‑06‑26).

## Current phase — Phase 35: deep architecture audit → "make it real"
**Research pass (done):** six parallel adversarial audits (verification core; safety/gateway/ops;
intelligence; data/physics; integration/boundaries; frontend/tests). Synthesis + prioritized, frozen‑tagged,
phased map in [`ARCHITECTURE_AUDIT.md`](ARCHITECTURE_AUDIT.md). Verdict: the core thesis is sound and honest;
the gap between *claims* and *proofs* concentrates in machine‑agnostic leakage, un‑calibrated "depth"
analytics, toy data, a few overshooting self‑claims, and frontend caveats dropped in transit.

**Phase 35a — honesty quick wins (COMPLETE, 2026‑06‑26):**
- [x] **B1** — an absent `X-VRA-User` is the supervisor ONLY in demo mode; otherwise 401 (no anonymous
      elevation). `auth.py`, `security.py`.
- [x] **B3** — telemetry provenance is the sample's *real* source + age, not a hardcoded
      `("SyntheticEfficastPort", 2)` (which lied on ingested data). `services/telemetry.py`, `cycle_engine.py`.
- [x] **A3** — timeline `is_recurrence` and outcome before/after fault labels derive from `incident.fault_code`,
      not the literal "F27". `api/serializers.py`.
- [x] Tests: `test_phase35_honesty.py` (6). Backend **113** green; hero demo → VERIFIED_RECOVERY.

**Phase 35b — machine-agnostic core (in progress):**
- [x] **A1** — the deterministic evaluator is now key-driven: `signal_value()` resolves a condition key
      to a first-class column *or* the machine-class signal in `obs.raw`; `is_stable_observation` and the
      scalar path are generic over the contract's conditions (any op), not the four conveyor metrics.
      `cycle_engine` now carries non-standard sample signals into `obs.raw`. `services/evaluator.py`,
      `services/cycle_engine.py`.
- [x] **A1 proof** — `test_machine_agnostic.py` (4): an **injection press** (IMX-90, fault E12, signals
      `melt_temperature`/`injection_pressure` via obs.raw) drives through the SAME evaluator + cycle engine
      to **VERIFIED**; an out-of-spec press signal resets the streak; a press relapse → `violated`. Backend
      **117** green; conveyor hero unchanged.
- [ ] **A2** — profile-driven reopen/contingency (the press relapse→reopen→contingency→verify arc) needs the
      conveyor-wired orchestrator (`draft_contract`, `reopen_with_contingency`, `approve/complete_contingency`
      — coupled to `contract_templates` + seed IDs like `bearing_part`/`tech_ortiz`) generalized to the
      profile catalog. Larger than a unit; carried into the orchestrator-generalization step.
- [ ] **A5/A6/A7** — one source of truth for the stable streak; drop the `max(10,…)` floor + builder check;
      enforce `max_duration_min` and unmatched-secondary-fault escalation.

**Phase 35c+ / 36–40 (planned, see the map):** 35b machine‑agnostic core (A1 key‑driven evaluator, A2 data‑driven
reopen, a 2nd machine end‑to‑end); 36 mind‑blowing data (seeded generative physics, fleet, scenario library);
37 research‑grade intelligence (calibration harness, stochastic precursor, honest SPRT/RAG); 38 safety/integrity
(audit anchor, ingest‑via‑gateway, port‑mediated reads); 39 frontend truth + negative‑path tests; 40 integration
proof (2nd EfficastPort). **[infra]** items (OIDC multi‑tenant, broker exactly‑once, concurrent‑writer tests)
stay deferred — verified honestly only on Postgres/a broker.
