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

**Baseline:** backend **117 pytest** passing · frontend **24 vitest** passing · typecheck/lint/build clean.

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
