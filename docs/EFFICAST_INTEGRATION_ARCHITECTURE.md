# Efficast Integration Architecture (readiness, v0.1)

*Status: **integration-ready, not integrated.** We make Verified Recovery ready to integrate with Efficast
through a narrow, versioned, testable seam — while preserving the synthetic demo and **assuming no access**
to Efficast's private API, database, cloud, or customer data. Nothing here claims a live connection.*

## The layers (data flows top → bottom)
```
host MES (Efficast)            ← NOT assumed; see EFFICAST_OPEN_QUESTIONS.md
   │  sanitised, enveloped events (contract v0.1)
   ▼
EfficastRecoveryPort           app/integration/efficast/recovery_port.py   (the versioned boundary)
   │  implemented by 3 adapters:
   ├── SyntheticEfficastAdapter   canned F27 scenario as contract events (the demo)
   ├── ReplayEfficastAdapter      reads a sanitised JSONL/CSV/Parquet bundle, replays by event time
   └── SandboxEfficastAdapter     interface + config ONLY — raises until a real endpoint is agreed
   ▼
reconciliation.py              dedup · order · lateness · clock-drift · unit · mapping-version · partial
   ▼
shadow.py                      evaluate (real cores) → propose disposition → compare to actual → NO writes
   ▼
(future) live mode             proposals through the existing Agent Action Gateway (APPROVAL_REQUIRED)
```

## Why this is additive (and safe)
- It sits **beside** the existing hexagonal `EfficastPort` (the app's runtime port) — the composition root
  and the 165→181 tests are untouched. `EfficastRecoveryPort` is the *integration contract*; adapters feed
  the same deterministic evaluator the demo uses (via the telemetry-ingest seam that already exists).
- **Reuse, not reinvention:** dedup/idempotency, the transactional outbox, hash-chained audit, and
  correlation IDs already exist for live writes (`gateway/idempotency.py`, `workflow/audit.py`); the new
  reconciler is the read-side complement for replay/shadow. The recovery signature (`score_observations`)
  and comparable-conditions (`classify_context`) cores are reused verbatim in shadow mode.
- **No machine control, by construction:** `EfficastRecoveryPort` has read + *proposal* methods only — no
  start/stop/setpoint/interlock/quality-release. Those remain in the frozen `PROHIBITED_ACTIONS` set.

## Shadow mode is the trust-earning mechanism
The honest path to a real integration is: run the agent's deterministic evaluation against real (sanitised)
event streams, record the **proposed disposition**, compare it to the plant's **actual outcome**, and write
**nothing**. `shadow.run_shadow()` takes no DB session and calls no write path — the no-write guarantee is
structural. The agreement record is the evidence that justifies ever moving to proposal mode.

## Sequencing
- **42a (this)** — data contract + envelope + `EfficastRecoveryPort` + 3 adapters + docs.
- **42b (this)** — Replay adapter + reconciliation + shadow mode + integration tests.
- **42c (next)** — Sensor Trust Gate (derive TRUSTED/DEGRADED/UNTRUSTED/UNKNOWN) + Lot-at-Risk analysis.
- **42d (next)** — structured outbound MAIA messages + role-specific stakeholder views.

See `EFFICAST_RECOVERY_DATA_CONTRACT.md` (the schema), `EFFICAST_OPEN_QUESTIONS.md` (what we need from
Efficast), and `REAL_DATA_PILOT_PLAN.md` (how a pilot would actually run).
