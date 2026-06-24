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

**Baseline:** backend **101 pytest** passing · frontend **22 vitest** passing · typecheck/lint/build clean.

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

## Next phase — Phase 34 (candidate; not started)
Either (a) the deferred MEDIUMs above as small tested units (M‑C derive‑from‑incident; C2 freshness‑at‑
closure), or (b) the infra batch (real authn/multi‑tenancy, durable scheduler + outbox worker,
semantic‑embedding RAG) — which needs a Postgres/broker environment to build *and verify* honestly.
