# Discovery Q&A — the 12 questions, answered with evidence

Two kinds of question are mixed here. **About our system** → answered with `file:line` + a test (no
claim exceeds what the code proves). **About Efficast's own product/customers** → we cannot assert facts
about another company's internals, so those are tagged **INFERRED** (from the public site/brief) or
**UNKNOWN** and framed as questions to confirm — the honest posture from `docs/EFFICAST_EVIDENCE_LEDGER.md`.

---

### 1. After MAIA recommends an action, what work still happens manually before the plant considers it resolved?
**Type: discovery (INFERRED).** From the public product, MAIA detects/alerts/closes work orders; the
*physical* repair, the judgment that "it's fixed," the cross‑shift coordination, and the work‑order close
are human. The manual gap we target is **verification** — proving the line actually recovered after the
checkbox. *To confirm with Efficast; not asserted.*

### 2. When a technician marks a work order complete, how does Efficast prove production recovered?
**Type: discovery (INFERRED) + our answer (PROVEN).** The thesis is that "complete" ≠ "recovered." **Our
mechanism:** a deterministic **Recovery Contract** ([`domain/contract.py`](../backend/app/domain/contract.py))
evaluated cycle‑by‑cycle against post‑intervention telemetry by [`services/evaluator.py`](../backend/app/services/evaluator.py)
— closure requires *all conditions PASSED for the full window AND quality release*, never a checkbox.
Proven by `tests/test_agent_eval.py` (never false‑closes a relapse).

### 3. Can it auto‑reopen if the same fault returns during the verification window?
**Efficast: UNKNOWN. Ours: YES.** `services/policy.py:should_reopen` (any `fault_*` recurrence) + the
cycle‑17 branch in [`workflow/reopening.py`](../backend/app/workflow/reopening.py) → reopen + contingency.
Proven by `tests/helpers.py:to_reopened` and `tests/test_safety.py`. (Hardened in Phase 29: **any** active
fault — not just the originating code — breaks the stable streak.)

### 4. Does MAIA maintain long‑running incident state across hours/shifts?
**Efficast: UNKNOWN.** **Ours: YES** — an 18‑state durable workflow (`workflow/state_machine.py`) with a
persisted `Incident` + `RecoveryWindow` (`stable_streak`, `observed_cycles`), surviving across cycles and
two verification windows. State is in the DB, not in an LLM context.

### 5. Are you already building Recovery Contract / stable‑cycle verification / false‑closure detection?
**YES — this is the core, not a roadmap item.** Recovery Contract (`domain/contract.py`); stable‑cycle
verification (`evaluator.is_stable_observation` + `stable_streak`, `COUNT_GTE`); false‑closure detection
(the `NOT_RECUR` condition + the deterministic verdict, with the **counterfactual calibration** in
`services/sensitivity.py` proving any window ≤16 would have false‑closed before the cycle‑17 relapse).

### 6. What still happens in WhatsApp / calls / spreadsheets after an alert?
**Type: discovery (INFERRED).** Triage decisions, "who's fixing it," evidence hand‑off, and approvals are
typically ad‑hoc. **What we replace it with:** a structured triage → human‑accept → role‑assigned evidence
→ approval‑gated closure workflow (`workflow/recovery_service.py`), with notifications. *Exact current
workflow to confirm with Efficast.*

### 7. Which evidence would a plant manager require before trusting verified closure?
**Ours, concretely:** role‑assigned, fresh, **validated** evidence per the contract
(`services/evidence.py`, `services/quality.py` — quality release needs a QUALITY_ENGINEER); plus, for
*trust in the closure itself*: GRADE‑style **evidence quality** weighting (`services/evidence_quality.py`),
the **closure‑provenance** record + proposed‑vs‑executed **reconciliation** (`services/provenance.py`), and
the **tamper‑evident audit chain** (`workflow/audit.py`, now signing attribution fields). All read‑only.

### 8. Can it connect machine, production, quality, lot, worker, and planner context into one incident?
**Efficast: UNKNOWN. Ours: YES** — the `EfficastPort` exposes exactly those domains (snapshot/OEE/
consumption/order/quality/lots/inventory/worker‑evidence/schedule; [`adapters/efficast_port.py`](../backend/app/adapters/efficast_port.py)),
and the `Incident` links machine + order + lots + interventions + evidence + audit into one record.

### 9. Which actions can agents execute automatically, and which always require human approval?
**Defined by `ActionClass`** (`gateway/actions.py`): `READ_ONLY` + `REVERSIBLE_AUTOMATIC` run
automatically (e.g. request evidence); `APPROVAL_REQUIRED` / `requires_human` (record approval, quality
release) are **blocked for the non‑human AGENT principal** at the gateway; `PROHIBITED` (all machine
control) never runs. Proven by the allowlist invariant + role/human‑gate tests in `tests/test_safety.py`.

### 10. Where would a specialized recovery agent fit best inside Efficast's architecture?
**Our answer (the "where in Efficast" part is INFERRED):** as a **verification layer** that *consumes*
host telemetry/alerts read‑only via `EfficastPort` and *publishes its verdict back*
(`publish_recovery_decision`). The seam + closed loop are specified in
[`EFFICAST_INTEGRATION_SPEC.md`](EFFICAST_INTEGRATION_SPEC.md); swapping synthetic→real is a one‑module
change in `app/composition.py`. The exact placement in Efficast's stack is a question for them.

### 11. What makes this meaningfully valuable rather than just an impressive demo?
It **changes an outcome a plant pays for**: it catches a *false recovery* (cycle‑17) that a detect‑and‑
close loop ships as "done," **auto‑reopens** instead of silently relapsing, and produces an **auditable,
trust‑weighted reason** for every closure. It's **deterministic** (a verdict you can defend, not a
probability), **machine‑agnostic** (profile‑driven), and **honest** (the analytics say plainly when
they're heuristic). Value = fewer false closures, fewer repeat alerts, a defensible closure record — not a
prettier dashboard.

### 12. What would make you reject the idea?
**Honest kill‑criteria.** Reject if: (a) Efficast already verifies post‑repair recovery (then we're
redundant — Q2/Q3 are the test); (b) the host can't expose the needed context **read‑only** (the
integration premise fails); (c) real post‑intervention telemetry is too noisy for a crisp deterministic
contract (then the contract needs statistical tolerance — partially addressed by the reliability layer,
but a real risk); (d) the residual gaps make it non‑deployable for a pilot — **and these are real and
disclosed**: no production auth/multi‑tenancy yet, no wall‑clock scheduler/durable outbox worker,
synthetic physics, lexical RAG (see `docs/SYSTEM_OVERVIEW.md` §7). We'd rather you reject it for a true
reason than be sold an unverifiable one.

---

**Net:** Q2–Q5, Q7–Q9, Q11 are answered by working, tested code today; Q1/Q4/Q6/Q8(Efficast side)/Q10
depend on Efficast internals we don't assert (recorded in `docs/RESEARCH_GAPS.md`); Q12 is answered with
real kill‑criteria, not spin.
