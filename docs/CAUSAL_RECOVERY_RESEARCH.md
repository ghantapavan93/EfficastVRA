# Recovery Assurance — research dossier & build plan (Phase 36 R&D)

*Established 2026‑06‑26. Synthesis of four parallel, web‑grounded research tracks (novelty/category;
causal‑consistency model + signature; contract DSL + state machine; evaluation/data/verdict). Confidence
tags: VERIFIED / STRONG / WEAK / PROTOTYPE‑ASSUMPTION / OPEN‑QUESTION. This is the decision layer; each
track's full sourced analysis fed these conclusions.*

> **Frozen‑decision check:** the whole direction is an **advisory** evolution. The deterministic evaluator
> still solely owns closure; the new layer annotates, never decides. No frozen decision changes.

## Executive verdict — GO, conditional (STRONG)
The deterministic, human‑gated, audited verification spine is genuinely well‑built and *honestly labelled*
— rare. The thesis ("a closed work order ≠ a recovered line") is sound and under‑served. **But today the
system *proves* less than the UI *claims*:** the "intelligence" speaks calibrated‑inference language over
hand‑tuned/read‑back numbers, and reliability rests on ~5 noiseless scenarios. **GO is gated on three
falsifiable deliverables:** (1) ≥3 machine families driven end‑to‑end through an adversarial suite with
**0 false closures + a reported confidence bound**; (2) ≥1 advisory number carrying a **real Brier score +
reliability diagram** on held‑out scenarios; (3) synthetic trajectories shown to fall within the **envelope
of a named public dataset** (NASA C‑MAPSS or IMS bearings). Hit those → "defensible prototype." Miss them →
it stays a "beautifully‑audited demo."

## Novelty — it's a layer, not a category (STRONG)
Prior art exists for every individual primitive: **CAPA effectiveness check** (ISO 9001 §10.2 — define
measurable criteria at approval time, monitor a window, reopen on recurrence = *our exact thesis*);
**return‑to‑service / post‑maintenance testing** (FAA Part 43, pharma IQ/OQ/PQ, nuclear ASME OM, semi
"marathon" qual); **golden‑batch fingerprint + similarity score** (TrendMiner/Imubit — *ships today*);
**auto‑reopen** (SRE auto‑rollback, eQMS CAPA reopen). **Smallest defensible novelty claim (STRONG):**
*"a deterministic, telemetry‑driven verification layer that, after a specific intervention, checks an
intervention‑conditioned recovery contract cycle‑by‑cycle against live data, auto‑reopens on relapse, and
gates closure on a non‑overridable verdict — bringing regulated‑world return‑to‑service discipline to
general discrete manufacturing, as software."* **Two moats that are hard to copy:** (1) a **conditional
intervention→signature outcome library** (data network effect — also what would *earn* the word "causal"),
(2) **verifiable‑by‑construction closure** (the LLM‑can't‑close architecture an "agentic" competitor can't
retrofit).

### Terminology decisions (apply going forward)
| Primitive | Decision | Plant‑legible term |
|---|---|---|
| Recovery **Contract** | keep brand; sell as the known concept | "recovery **acceptance criteria** / return‑to‑service criteria" |
| Recovery **Fingerprint** | **RENAME** (collides with golden‑batch fingerprint) | **Expected Recovery Signature** (intervention‑conditioned) |
| Recovery **Certificate** | **keep — strongest primitive** | "**Return‑to‑Service Certificate**" (a software maintenance release) |
| "**Causal** Recovery Assurance" | **drop "causal" from headline** until matched‑conditions counterfactual exists | "**intervention‑consistency** / condition‑matched verification" |

**Claims we must NOT make:** "first to verify a repair worked" (CAPA/PMT predate us); "novel fingerprint"
(golden‑batch); "new category"; "regulated‑compliant" (we're *regulated‑inspired*, synthetic, unvalidated);
any Efficast specific beyond the public site.

## The causal‑consistency model (advisory, deterministic) — STRONG
A strictly weaker, hedged claim than the evaluator's factual closure: *"the post‑intervention trajectory is
**consistent with** the hypothesis that this intervention caused the improvement, vs temporary suppression /
regression‑to‑mean / changed conditions / noise."* Each rival explanation gets a deterministic guard:
suppression → fault‑absence **and** precursor‑flat; RTM/noise → sustained in‑spec run ≥ `cycles_required` +
SPC run‑rules; changed conditions → an **operating‑conditions‑matched** flag (currently `UNKNOWN` — we
**surface the confound we can't rule out**, never hide it). Methods triaged (web‑grounded): adopt the **ITS
framing** + **Nelson/Western‑Electric run rules** + **CUSUM** (corroboration) + keep the existing **SPRT**
and **zero‑failure reliability** math; **defer synthetic‑control / diff‑in‑diff** (misleading at N=1 — need
the fleet seed first).

### The ladder (advisory; never the closure verdict, never "proof")
`INSUFFICIENT_EVIDENCE → RECOVERY_OBSERVED → CONSISTENT_WITH_INTERVENTION → STRONGLY_CONSISTENT`
with two mandatory **honesty caps**: (a) *conditions‑unverified* — top rung always flagged because
load/product/speed aren't captured yet; (b) *precursor‑rising* — a climbing precursor caps the rung below
strongly‑consistent even if the SPRT would accept (wires the forecaster's warning into the read, closing the
SPRT's own admitted blind spot).

### Expected Recovery Signature (the implementable primitive)
Derived from the contract's conditions — `LTE/LT→down`, `GTE/GT→up`, `WITHIN_PCT→converge`,
`DECLINING→down`, `NOT_RECUR→absent`, deadline→speed — **plus** the monitored degradation precursor
(`flat_or_down`). Machine‑agnostic (no F27/bearing literals). Scoring: per‑signal agreement `aᵢ ∈ [−1,1]`,
weighted (fault‑absence + precursor outweigh headline metrics because they discriminate a real fix from
symptom suppression), `alignment = Σwᵢaᵢ / Σwᵢ`. **Hero worked example:** window‑1 (alignment) → `alignment
≈ +0.17`, rung `RECOVERY_OBSERVED` (fault recurs + precursor rises); window‑2 (bearing) → `alignment ≈ +1.0`,
rung `STRONGLY_CONSISTENT (conditions‑unverified)` — *same headline metrics, opposite signatures.* That
discrimination is the demo's punchline and nothing in the current stack produces it cleanly.

## Contract DSL + state machine (STRONG)
**Keep the typed‑condition DSL** — it already has the temporal operators (`count_gte`, `not_recur over
window`, deadline‑bounded compares) that CEL/Rego/JSON‑Logic/DMN/BPMN/XState all lack (they're stateless
single‑pass evaluators). Borrow CEL's **invariants** (totality, purity, linear cost) and the
**runtime‑verification** framing (the evaluator is an online monitor of signal‑temporal properties).
**Evolve, don't rewrite:** add `schema_version` + `content_hash` + per‑condition `provenance` (source +
evidence‑tag), snapshot resolved `cycle_seconds` for replay, generalize the vacuity guard into a full
**validation/conflict pass**. **State machine:** split into **Incident lifecycle (~7 states)** ×
**Recovery‑attempt lifecycle (~5 states)**; the append‑only audit log is the **source of truth**, the
`state` column a derived cache; reopening = **new attempt + new contract version**, not a rewind.

## Evaluation & data (STRONG)
**Primary metric: Verified‑Closure Integrity** — false‑closure rate at a fixed over‑reopen budget, reported
**with a confidence bound and N** (rule of three: ~300 relapse scenarios with 0 failures to claim <1%).
Cost matrix `C_false_closure : C_over_reopen ≈ 20–50:1` (env‑configurable PROTOTYPE_ASSUMPTION). 7‑layer
rubric (L1–L5 deterministic golden assertions; L6 statistical calibration; L7 frontend negative‑path).
**12 mandatory adversarial scenarios** (metric‑nominal relapse, vacuous contract, recover‑then‑drift,
stale‑evidence TOCTOU, forged telemetry, self‑approval, prompt‑injection, audit tail‑truncation,
anonymous‑as‑supervisor, sensor‑dropout, unmatched secondary fault, over‑reopen) — half map to still‑open
audit gaps (ship as xfail). **Anti‑overfit to cycle‑17:** randomize the relapse cycle, hold out the hero
family, use property‑based assertions, mutation‑test derived outputs. **Synthetic factory:** seeded
generative physics (degradation‑as‑state + coupling + noise + emergent faults), fleet seed, scenario
library; validate trajectory *statistics* against **NASA C‑MAPSS / IMS bearings (acknowledge‑only)** and
**SECOM (CC‑BY‑4.0)** via an optional offline script (don't redistribute datasets).

## Moat shortlist — the two winners (STRONG)
1. **False‑Closure Risk Score (FCRS)** — a pre‑closure, read‑only, *calibrated* estimate that this specific
   closure is false (from precursor trajectory + evidence completeness + streak margin + SPRT state +
   historical relapse rate). It *is* the thesis as a falsifiable number, and the natural home for the
   calibration harness. Max moat, max MVP‑fit, low Efficast overlap.
2. **Intervention Effectiveness / Signature library** — per‑fix verified‑recovery rate, median TTVR, relapse
   rate, accumulated across the fleet + knowledge loop; the backward‑looking evidence that feeds FCRS.
   *Cut:* cross‑domain closure graph, recovery‑policy compiler, transfer learning, standalone analytics,
   memory decay, counterfactual plan comparison, evidence‑acquisition planner, recovery debt, certificate‑
   as‑headline (keep certificate as a thin export of the existing closure‑provenance record).

## Build plan (phased; each a small tested unit; preserve the hero)
- **36a (DONE this pass): Expected Recovery Signature scorer** — `services/recovery_signature.py`
  `score_signature()` (advisory, read‑only, derived‑from‑contract, the ladder + honesty caps), with tests
  proving the hero's two windows score oppositely. The single highest‑value unit (both causal + eval tracks
  agree).
- **36b:** read‑only `/api/incidents/{id}/signature` route + serializer + a UI card (with caveat chips, per
  the frontend‑truthfulness fixes F1/F2).
- **36c:** the calibration harness (Brier / reliability diagram / ROC / lead‑time) — requires the stochastic
  precursor; ships with it.
- **37 (data):** seeded generative physics → fleet seed → scenario library (hero‑pinned). Unlocks the
  adversarial suite breadth + the calibration numbers + the public‑dataset validation.
- **38:** the adversarial golden suite (12 scenarios, L1–L5 deterministic assertions) — converts the audit's
  open gaps into CI.
- **39:** FCRS (moat winner #1) on top of the signature + calibration.
- **Reproducibility/DSL track (parallel, low‑risk):** `schema_version` + `content_hash` + per‑condition
  provenance + golden‑replay test + the validation/conflict pass (Agent C steps 1–3).

**The #1 limitation to state plainly (Agent D):** everything is downstream of *contract correctness* — a
profile‑derived contract is a PROTOTYPE_ASSUMPTION; if it tests the wrong thing, the system confidently
verifies a recovery that didn't happen, and the audit will still read "clean." Contract quality must itself
be evaluated (the vacuous‑contract test is a start) and can never be fully discharged on synthetic data.
