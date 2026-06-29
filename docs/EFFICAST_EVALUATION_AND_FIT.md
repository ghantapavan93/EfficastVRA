# Efficast Evaluation & Fit — an evaluator's-eye view

*What an Efficast technical/product team would scrutinise if they looked closely, what is genuinely
defensible, and how deeply this could plug into their stack. Honest by discipline: our own capabilities are
**VERIFIED-by-code** (file references given); everything about Efficast's internals (private API, DB, model
providers, sensor mix per customer) is **UNKNOWN** and never asserted. Not affiliated with Efficast.*

---

## 0. The one-sentence thesis they'd test
Efficast (and MAIA) **close** work orders and show **OEE**. We claim a closed work order is not proof the line
recovered, and we **verify recovery after the intervention** against a deterministic **Recovery Contract**,
**reopening on relapse**. So the first thing they'd probe is: *does this catch real false closures that MAIA's
closure flow misses — on our data, not your synthetic demo?*

---

## 1. What Efficast's people would check (technical due diligence)

### A. Engineering / platform lead — "Is this real, and what does it cost us to connect?"
| They'd ask | Honest answer | Where it lives |
|---|---|---|
| *What data do you need, at what cadence?* | 12 typed reads. The **OEE-native** fields (cycle time, scrap, fault/stoppage, work orders, quality checks, lots, planner impact) are **enough for the OEE-restoration path**. Vibration/temperature/bearing-precursor are **optional** condition-monitoring signals that sharpen the mechanical-fault signature but aren't required. | `integration/efficast/recovery_port.py`, `services/oee_restoration.py` |
| *Does it write to our system?* | **No.** Shadow mode takes no DB session and calls no write methods — the no-write guarantee is **structural** (`writes_performed = 0`), not a promise. Proposals (reopen, request-evidence) are **advisory** envelopes you may act on. | `integration/efficast/shadow.py`, `recovery_port.py` (no machine-control methods exist) |
| *Prove the LLM can't close an order or touch a machine.* | A model's recommendation is bound to a safe maintenance catalog; an architecture **fitness test** fails if any machine-control capability appears; closure is decided by code, not the model. All runnable. | `gateway/actions.py::PROHIBITED_ACTIONS`, `tests/test_architecture.py`, `tests/test_agent_reasoning.py` (rejects `machine_restart`) |
| *Is the trail tamper-evident?* | Per-correlation SHA-256 hash chain, optionally **HMAC-signed** (unforgeable without the key); a `verify` endpoint recomputes it live. | `workflow/audit.py`, `/api/security` |
| *Will it scale to N tenants × M machines?* | Tenant/plant scoping on every read+action; Postgres-ready. **Honest gap:** concurrent-writer correctness is proven only on Postgres, not the SQLite demo. | `docs/IMPLEMENTATION_PLAN.md` `[infra]` items |
| *How do we feed it without live access?* | A **Replay** adapter consumes a sanitised event export; **reconciliation** handles dedup, out-of-order, clock drift, unit mismatch, and mapping-version changes before anything is scored. | `adapters/replay.py`, `reconciliation.py` |

### B. Product / quality lead — "Does it catch what we miss?"
- **The false-closure case:** an intervention's work order completes, early cycles look recovered, then the
  originating fault **recurs mid-window → the incident auto-reopens.** They'd want this reproduced on *their*
  history via **shadow mode**, which emits an **agreement rate** vs the outcome the plant actually reached.
- **Causal honesty:** the **Comparable-Conditions Gate** refuses to credit a "recovery" if before/after ran
  under different product/speed/load/sensor-health (default-deny on confounds). Most dashboards would have
  shown green.
- **OEE as the verdict, not just the chart:** OEE-Restoration recomputes **A×P×Q vs baseline** and names the
  **lagging factor** ("closed, but performance is still 6 pts below baseline"). This speaks their metric.
- **Honest limit they'd flag:** our calibration (Brier ≈ 0.14, AUC ≈ 0.99) is measured on **synthetic**
  scenarios — it shows the signature's *internal* skill, not real-world predictive power. Real-data
  re-calibration is a precondition, not a footnote.

### C. Calibration / data science — "Where do the numbers come from?"
Every threshold — 30 stable cycles, SPRT bounds, OEE restoration tolerance, cost/severity — is a
**`PROTOTYPE_ASSUMPTION`**, env-configurable, **not** a claim about any real line. The engine is **machine-
agnostic** (the same evaluator drives a conveyor, an injection press, and a hydraulic unit from a *profile*,
not new code), so onboarding a machine class is data + a profile, not a rewrite. But the specific numbers
**must be fit to Efficast's data per machine class/customer** — they'd treat that as the real integration work.

### D. Architecture / UX — "Does it fight MAIA?"
No — it sits **after** MAIA. MAIA triages and closes the OT; we open a verification window on that closure and,
on relapse, raise an **advisory** `propose_incident_reopen` that can surface through MAIA's own WhatsApp
channel. The risk they'd weigh is operator confusion ("MAIA said done, this says reopened") — which is exactly
the point, surfaced deliberately, with the evidence attached.

---

## 2. The uniqueness factor (what's actually defensible)

**Commodity (they or competitors already have it):** OEE dashboards, anomaly alerts, RAG over manuals, an LLM
chat/agent, work-order management. We do **not** claim novelty here.

**Defensible — the moat:**
1. **The Recovery Contract** — recovery defined as a *falsifiable, machine-checkable* artifact (conditions +
   stable window + quality gate + reopen policy), not a status field. This is the core new primitive.
2. **Deterministic evaluator owns closure; the LLM is strictly advisory.** The inversion of "let the agent
   close the loop." For quality-sensitive / regulated manufacturing this is a *governance* differentiator.
3. **Reopen-on-relapse** — verification continues *past* closure; closure is not terminal.
4. **Comparable-Conditions Gate** — refuses to attribute an apparent recovery to the intervention when
   conditions weren't comparable. Genuinely novel causal discipline.
5. **OEE-Restoration as verification** — not "is OEE high" but "did *this recovery* restore OEE, and which
   factor still lags." Their metric, our lens.
6. **Tamper-evident, optionally-signed audit + integrity-applied-to-itself** (every external claim tagged
   VERIFIED/OBSERVED/INFERRED/UNKNOWN). A *trust* differentiator, not just a feature.
7. **A category, not a feature: Post-Intervention Production Requalification (PIPR)** — the manufacturing
   analogue of aviation Return-to-Service, pharma IQ/OQ/PQ + CPV, and nuclear post-maintenance testing. This
   gives Efficast a **regulated-industry expansion narrative** they don't currently frame.

> **The moat in one line:** it's a **verification layer, not another monitoring layer.** Everyone monitors;
> nobody *contracts* a recovery, *verifies* it across a window, and *reopens* on relapse — with the model kept
> out of the verdict.

---

## 3. How deeply they could integrate it

Three tiers, lowest-risk first. **Tiers 0–1 exist today as documented seams** (port + shadow + replay +
reconciliation); **Tier 2 needs Efficast internals we deliberately don't have or claim.**

| Tier | What it is | What Efficast provides | Writes to Efficast? | Effort | Status |
|---|---|---|---|---|---|
| **0 · Shadow** | Read-only event feed → run the *same* deterministic cores → a "Verified / Not-verified / Insufficient" verdict + OEE-restoration on a side dashboard; report **agreement rate, confusion matrix, Cohen's κ, and false-closure recall** vs actual outcomes | a sanitised export **or** read-only stream | **None** (structural) | Low (weeks) | **Built + scored** — `GET /api/integration/shadow`, `services/shadow_scorecard.py`, System-page scorecard |
| **1 · MAIA handoff** | MAIA closes an OT → event opens a Recovery Contract + window → on relapse, an **advisory** reopen + a recovery report back through MAIA's WhatsApp channel | an "OT closed" event + a channel to receive an advisory "reopen recommended" | Advisory proposals only | Medium (1–2 mo) | **Seam built** (`propose_incident_reopen`, `publish_recovery_status`, `maia.py`); needs their event/webhook |
| **2 · Native module** | "Recovery Verification" becomes a 10th Efficast module — shared data model, auth, UI; `EfficastPort` becomes a real adapter to their internal API/DB | internal API/DB access, SSO, UI surface | Through their own gateway | High (quarters) | **Not built** — requires internals tagged UNKNOWN |

### Data-fit map — why Tier 0 is realistic (no new sensors)
Our contract events were shaped to mirror Efficast's actual module surface:

| Our contract event | Efficast module it reads from | Needs new sensors? |
|---|---|---|
| `ProductionCycle` (cycle time, good/scrap) | **Automatic OEE** (A·P·Q) | No |
| `MachineEvent` (stoppage / fault F27) | **Live View** | No |
| `WorkOrder` / `Intervention` | **Production Orders (OF/OT)** | No |
| `QualityCheck` | **Quality** | No |
| `LotTrace` | **Stock & Traceability** | No |
| `PlannerImpact` | **Planner** | No |
| `OperatorObservation` | **Worker View** | No |
| `TelemetryObservation` (vibration/temperature) | sensor layer / **Efficast Edge** | **Optional** — only for the mechanical-fault *signature*; the **OEE-restoration verdict runs without it** |

**The wedge:** the OEE-restoration path verifies recovery using only data Efficast already collects
(cycle time, scrap, stoppages). Condition-monitoring (vibration/temperature) is an *upsell* that sharpens
root-cause + early-warning, not a prerequisite. So a pilot can start on a customer's existing OEE stream.

---

## 4. The honest gaps they'd (rightly) hold us to
- **Real-data validation** — calibration/agreement are synthetic until run on a sanitised Efficast export.
- **Threshold fitting** — every figure is a `PROTOTYPE_ASSUMPTION` needing per-machine-class calibration.
- **Their internals are UNKNOWN** — Tier 2 is a design, not a connection; we make no API/partnership claim.
- **Sensor reality per customer** — the vibration-rich signature assumes CM sensors a given site may not have;
  the OEE path is the safe default.
- **Deployment hardening** — TLS, a vault/KMS-sourced audit-signing key, SIEM, distributed rate limiting, and
  concurrent-writer proofs on Postgres are deployment-stage (see `docs/THREAT_MODEL.md`, `SECURITY_HARDENING.md`).

**Bottom line for an Efficast evaluator:** low integration risk (read-only, no machine control, structural
no-write), a verdict in their own OEE language, and a genuinely new primitive (contracted, reopenable,
model-out-of-the-loop recovery verification) — gated honestly on real-data calibration before anyone trusts a
number.
