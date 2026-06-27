# Real-Data Pilot Plan

*How Verified Recovery would move from synthetic demo → integrated, in **safe, reversible stages**, earning
trust before it ever proposes — let alone writes. No stage claims an Efficast connection until the prior
stage's exit criteria are met and tested.*

## Stage 0 — Synthetic shadow (DONE, today)
- **Input:** `fixtures.make_f27_bundle` (synthetic, contract-v0.1 enveloped).
- **What runs:** `run_shadow()` — reconcile → evaluate (real cores) → propose → compare to actual → no writes.
- **Exit:** integration + reconciliation tests green (they are); demoable end-to-end with zero deps.

## Stage 1 — Sanitised real export, offline shadow
- **Input:** a **sanitised** historical incident bundle from Efficast (no PII, no secrets), mapped to v0.1
  via a `mapping_version`. Delivered as JSONL/CSV/Parquet → `ReplayEfficastAdapter.from_jsonl`.
- **What runs:** shadow mode over real-shaped history; produce an **agreement report** (proposed vs actual
  disposition) + a reconciliation report (how messy the real stream is).
- **Exit criteria:** mapping authored + reviewed; reconciliation anomalies understood; agreement rate +
  disagreement analysis reviewed with Efficast. **Still zero writes.**
- *Resolves open questions:* data shape, identifiers, units, time, delivery semantics (from the export).

## Stage 2 — Live read-only shadow
- **Input:** a real **read-only** feed (the `Sandbox` adapter wired to an agreed endpoint/stream).
- **What runs:** continuous shadow on live data; rolling agreement + reconciliation dashboards.
- **Exit criteria:** stable agreement over N incidents; latency/ordering/idempotency behaviour characterised;
  sensor-trust + lot-at-risk (42c) validated against reality. **Still zero writes.**

## Stage 3 — Proposal mode (human-in-the-loop)
- **What changes:** proposals (`request_evidence`, `propose_incident_reopen`, `publish_recovery_status`,
  `create_recovery_debt_proposal`) are *delivered* — but every one is **advisory**, routed through the Agent
  Action Gateway, and acted on only by an authorised human. Still **no machine control, no auto-closure,
  no auto-quality-release** (frozen `PROHIBITED_ACTIONS`).
- **Exit criteria:** proposal precision/recall acceptable to plant + quality; audit trail reviewed; rollback
  plan exercised.

## Stage 4 — Steady state
- Proposal mode in routine use; the deterministic evaluator still owns every verdict; humans own every
  consequential action. Periodic re-validation of the agreement rate; contract version bumped as needed.

## Guardrails that hold at every stage
- The deterministic evaluator owns closure; the LLM never does.
- Every write goes through the Agent Action Gateway; the LLM proposes, humans approve.
- Shadow mode performs **no** writes (structural).
- We do **not** state "connected to Efficast" until Stage 2+ is live and tested on a real endpoint.
- All figures (thresholds, windows, SPRT) remain `PROTOTYPE_ASSUMPTION` until calibrated on real data.

## What we need to start Stage 1
A single **sanitised** historical incident bundle (intervention complete → verification window → outcome).
Everything downstream is already built and tested. See `EFFICAST_OPEN_QUESTIONS.md`.
