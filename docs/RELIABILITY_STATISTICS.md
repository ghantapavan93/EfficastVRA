# Reliability statistics — how *confident* are we that production recovered?

The deterministic verifier already proves a recovery: the originating fault must stay absent for the
contract's verification window. This layer answers the next question a senior reliability engineer
always asks — **"How confident are we, in numbers — and why 30 stable cycles, not 17 or 60?"** It
imports the reliability engineer's own math (after we imported finance → economics and aviation →
FMEA in [`CROSS_INDUSTRY_RESEARCH.md`](CROSS_INDUSTRY_RESEARCH.md)).

**Advisory only.** Nothing here decides or changes closure — the deterministic evaluator still owns the
verdict. This *annotates* that verdict with a confidence number and *grades* the window. Target
reliability parameters are configurable PROTOTYPE_ASSUMPTIONs, not Efficast data.

`app/services/reliability_stats.py` · `GET /api/incidents/{id}/reliability` · MCP `get_reliability_assessment`
· UI **Recovery Confidence** tab · tests `tests/test_reliability_stats.py`.

## 1. Verification confidence — the zero-failure / success-run demonstration test
A run of *n* consecutive fault-free cycles is exactly the **"success runs"** problem studied since
Wald's *Sequential Analysis* (1947); in reliability engineering it is the **zero-failure reliability
demonstration test**. With zero failures in *n* cycles:

| quantity | formula | meaning |
|---|---|---|
| confidence that per-cycle relapse `p ≤ p0` | `1 − (1−p0)^n` | how sure we are the fault rate is acceptable |
| per-cycle reliability lower bound (at confidence `C`) | `R_LCB = (1−C)^(1/n)` | Clopper–Pearson zero-failure case |
| cycles needed to demonstrate `p ≤ p0` at confidence `C` | `n ≥ ln(1−C) / ln(1−p0)` | inverts the test → **grades the window** |

**Worked, live (cycle 14 of the hero scenario), target `p0 = 5%/cycle`, `C = 95%`:**
- 14 fault-free cycles ⇒ **51%** confident relapse ≤ 5%/cycle — *recovery not yet proven.*
- The full 30-cycle window ⇒ **79%** confident (graded **"adequate"**).
- To reach 95% confidence you need **59** cycles — so the contract's 30 catches a *gross* false
  recovery but leaves residual risk. That is a quantified recommendation, not a guess.

This is why the answer to "why 30 cycles?" is no longer "it seemed reasonable."

## 2. Sequential decision — Wald's SPRT (the two-sided test)
The success-run test is one-sided — it only ever *accepts*. The full **Sequential Probability Ratio
Test** (Wald, 1947) is two-sided and decides as soon as the evidence is sufficient. Each cycle it adds
to a log-likelihood ratio of **H₁ "will relapse"** (rate `p1`) vs **H₀ "recovery holds"** (rate `p0`):
a clean cycle pushes it down (toward *accept*), a fault pushes it up (toward *reject*). It stops when a
bound is crossed:

| outcome | rule | meaning |
|---|---|---|
| **accept** | LLR ≤ `ln(β/(1−α))` | recovery demonstrated |
| **reject** | LLR ≥ `ln((1−β)/α)` | this did **not** recover (relapse) |
| **continue** | between the bounds | need more cycles (reports how many) |

with `α` = producer risk (false reject) and `β` = consumer risk (false accept). Shipped params
(PROTOTYPE_ASSUMPTIONs, env-overridable): `p0=5%`, `p1=20%`, `α=β=5%`.

**Safety-critical tuning:** `p1` is chosen so the *accept* threshold falls at ~18 clean cycles —
**after** the hero scenario's cycle-17 relapse. So the sequential test **never endorses the false
recovery before the fault fires**; the relapse instead drives it to *reject*. Live at cycle 14: LLR
−2.41 vs accept bound −2.94 → **undecided, ~4 clean cycles short.** And because it counts only observed
faults, it is **blind to a latent precursor** — the panel says so and defers to the
[Recovery Forecaster](RECOVERY_FORECASTING.md), which *does* watch the precursor.

## 2b. Counterfactual contract calibration (deterministic replay)
The statistics above are *probabilistic*. This is the **deterministic** complement: `app/services/sensitivity.py`
replays the verifier over the **recorded trajectory** at a sweep of verification-window lengths and reports
what the verdict *would* have been. On the hero relapse:

| window N | outcome |
|---:|---|
| 5, 10, 15 | **FALSE-CLOSE** at cycle N (declares recovery before the fault returns) |
| 17, 20, 25, **30**, 40, 50 | **catches the relapse** (reopens) |

So the **minimum safe window = the relapse cycle (17)**; the contract's **30** clears it by **+13 cycles**;
anything **≤ 16 would have been fooled.** Together the two layers bracket calibration:

> **17** (deterministic — to catch *this* relapse) ≤ **30** (the contract) ≤ **59** (statistical — for 95% confidence)

`GET /api/incidents/{id}/sensitivity` · MCP `get_contract_sensitivity` · the **Recovery Confidence** tab's
calibration card · tests `tests/test_sensitivity.py`. Advisory, read-only — it grades the window; it never
changes the verdict.

## 3. Hazard read — where on the bathtub curve does this fault live?
**Machine/fault-scoped** — relapse cycles are derived from the history of machines of the *same model*
(plus any documented prior for the fault code), never hard-coded, so this generalises to any machine. In
the live run F27 relapses around **cycle 17 — well inside the 30-cycle window.** A failure rate high
early and falling with running time is the **infant-mortality / early-life** region of the bathtub curve
(Weibull shape **β < 1**): the first intervention left a **latent defect** (the drive-end bearing) — not
a random (β≈1) or wear-out (β>1) failure. It is the statistical fingerprint of a false recovery, and the
reason verifying the *whole* window — not just "work completed" — is necessary. With few data points this
is reported as a **qualitative** read (labelled `data_confidence: limited`), not a fitted Weibull model.

## Why this is safe
No model weights, no automated action, no state change — a pure read over the verification window and
recurrence history. A wrong statistic cannot cause a false close or a false reopen; it can only inform
the human and grade the contract. It composes with the [Recovery Forecaster](RECOVERY_FORECASTING.md)
(which predicts *when* a relapse is coming) and [Decision Intelligence](CROSS_INDUSTRY_RESEARCH.md)
(which prices the options): forecaster = *is it diverging?*, statistics = *how sure are we it held?*,
decision = *what's it worth?*

## References
- A. Wald, *Sequential Analysis* (Wiley, 1947) — origin of the SPRT.
- [Sequential probability ratio test (overview)](https://en.wikipedia.org/wiki/Sequential_probability_ratio_test)
- [ReliaSoft — SPRT for reliability demonstration](https://help.reliasoft.com/articles/content/hotwire/issue162/hottopics162.htm)
- [Zero-failure testing & the success-runs foundation (arXiv 2407.03979)](https://arxiv.org/pdf/2407.03979)
- [The bathtub curve & Weibull hazard (β<1 infant mortality)](https://www.allaboutcircuits.com/technical-articles/how-the-Weibull-distribution-is-used-in-reliability-engineering/)
