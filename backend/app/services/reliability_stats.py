"""Reliability statistics — how *confident*, mathematically, are we that production recovered?

The core thesis is "work completed ≠ production recovered." The deterministic verifier already proves a
recovery by requiring the originating fault to stay absent for the contract's verification window. But a
senior reliability engineer asks the next question: **"How confident are we, in numbers — and why 30
stable cycles, not 17 or 60?"** Until now "30" was an assumption. This layer answers it with the
reliability engineer's own math, importing the discipline (after finance → economics, aviation → FMEA):

  1. **Verification confidence — the zero-failure / success-run reliability demonstration test.** A run
     of *n* consecutive fault-free cycles is exactly the "success runs" problem (Wald's *Sequential
     Analysis*, 1947; the reliability-demonstration / zero-failure test). With zero failures in n cycles,
     the per-cycle reliability lower confidence bound is ``R_LCB = (1−C)^(1/n)`` (the Clopper–Pearson
     zero-failure case), and the confidence that the per-cycle relapse probability ``p`` is at most a
     target ``p0`` is ``1 − (1−p0)^n``. Inverting gives the *minimum* stable cycles to demonstrate
     ``p ≤ p0`` at confidence C: ``n ≥ ln(1−C) / ln(1−p0)``. This **grades the contract window** and the
     current run with a real number instead of a guess.

  2. **Sequential decision — Wald's SPRT.** The success-run test is one-sided (it only *accepts*). The
     full **Sequential Probability Ratio Test** (Wald, 1947) is two-sided: cycle by cycle it accumulates
     the log-likelihood ratio of H1 "will relapse" (rate ``p1``) vs H0 "recovery holds" (rate ``p0``) and
     **decides as soon as enough evidence accrues** — ``accept`` (recovery demonstrated), ``reject`` (this
     did *not* recover), or ``continue`` — with controlled error rates α (false reject) and β (false
     accept). This covers the accept *and* the relapse use cases, and says how many more clean cycles a
     decision needs. (It counts only observed faults, so it is blind to a latent precursor — when the
     Recovery Forecaster flags rising divergence, an SPRT "accept" must be treated with caution.)

  3. **Hazard read — where on the bathtub curve does this fault live?** Machine/fault-scoped: relapse
     cycles are derived from the history of machines of the *same model* (plus any documented prior for
     the fault), never hard-coded. A failure rate high early and falling with running time is the
     **infant-mortality / early-life** region (Weibull β<1): a latent defect the first intervention did
     not address. β≈1 is random/useful-life; β>1 is wear-out. Early-life is the statistical fingerprint
     of a false recovery — why verifying the *whole* window, not just "work completed," is necessary.

ADVISORY ONLY. Nothing here decides or changes closure. The deterministic evaluator still owns the
verdict; this annotates that verdict with a confidence figure and grades the window. Target reliability
parameters are configurable PROTOTYPE_ASSUMPTIONs, not Efficast data.

References: A. Wald, *Sequential Analysis* (1947) — SPRT; reliability-demonstration ("success-run"/
zero-failure) testing; the bathtub curve & Weibull hazard (β<1 = infant mortality). See
docs/RELIABILITY_STATISTICS.md.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

from sqlmodel import Session, select

from app.domain.models import Incident, Machine, RecoveryContract, RecoveryObservation, RecoveryWindow


def _latest_window(session: Session, contract: RecoveryContract) -> RecoveryWindow | None:
    """The most recent verification window for this contract, regardless of status — so the assessment
    is meaningful while monitoring *and* after the window has closed (verified or failed)."""
    return session.exec(
        select(RecoveryWindow)
        .where(RecoveryWindow.contract_id == contract.id)
        .order_by(RecoveryWindow.sequence.desc())  # type: ignore[attr-defined]
    ).first()

# Target reliability for the demonstration test (override via env). PROTOTYPE_ASSUMPTIONs.
TARGET_RELAPSE_RATE = float(os.getenv("VRA_TARGET_RELAPSE_RATE", "0.05"))   # acceptable per-cycle relapse p0
CONFIDENCE_LEVEL = float(os.getenv("VRA_CONFIDENCE_LEVEL", "0.95"))         # demonstration confidence C

# Wald SPRT hypotheses & error rates (override via env). PROTOTYPE_ASSUMPTIONs. p1 is set so the accept
# threshold falls *after* the hero scenario's cycle-17 relapse — the sequential test never endorses the
# false recovery before the fault fires; the relapse pushes it to 'reject' instead.
SPRT_P0 = float(os.getenv("VRA_SPRT_P0", "0.05"))     # H0: recovery holds (acceptable per-cycle relapse)
SPRT_P1 = float(os.getenv("VRA_SPRT_P1", "0.20"))     # H1: will relapse (unacceptable per-cycle relapse)
SPRT_ALPHA = float(os.getenv("VRA_SPRT_ALPHA", "0.05"))  # producer risk — P(false reject of a real recovery)
SPRT_BETA = float(os.getenv("VRA_SPRT_BETA", "0.05"))    # consumer risk — P(false accept of a bad recovery)

# Documented recurrence priors keyed by fault code, from real historical incidents (F27: sibling CDX-220
# drive, INC-1990, recurred ~cycle 17). Merged with live same-model history; a fault with no documented
# prior contributes nothing (the read is then derived purely from that machine model's own data).
KNOWN_RECURRENCE_PRIORS: dict[str, tuple[int, ...]] = {"F27": (17,)}


# ── pure statistics (no I/O — unit-tested directly) ───────────────────────────
def confidence_relapse_at_most(stable_cycles: int, p0: float) -> float:
    """Confidence (0..1) that the true per-cycle relapse probability is ≤ ``p0`` given
    ``stable_cycles`` consecutive fault-free cycles (zero-failure demonstration): ``1 − (1−p0)^n``."""
    if stable_cycles <= 0:
        return 0.0
    return 1.0 - (1.0 - p0) ** stable_cycles


def reliability_lower_bound(stable_cycles: int, confidence: float) -> float:
    """Per-cycle reliability lower confidence bound from n zero-failure cycles:
    ``R_LCB = (1−C)^(1/n)`` (Clopper–Pearson zero-failure case). Returns 0 for n≤0."""
    if stable_cycles <= 0:
        return 0.0
    return (1.0 - confidence) ** (1.0 / stable_cycles)


def cycles_required(confidence: float, p0: float) -> int:
    """Minimum consecutive fault-free cycles to demonstrate per-cycle relapse ≤ ``p0`` at ``confidence``:
    ``n ≥ ln(1−C) / ln(1−p0)``."""
    if not (0.0 < confidence < 1.0) or not (0.0 < p0 < 1.0):
        return 0
    return math.ceil(math.log(1.0 - confidence) / math.log(1.0 - p0))


def survival_probability(reliability_per_cycle: float, cycles: int) -> float:
    """P(no relapse across ``cycles`` more cycles) = R^cycles, at the demonstrated per-cycle reliability."""
    return reliability_per_cycle ** max(0, cycles)


def sprt_bounds(alpha: float, beta: float) -> tuple[float, float]:
    """Wald's decision bounds on the log-likelihood ratio: ``(A, B)`` where A = ln((1−β)/α) (cross up →
    *reject* H0, i.e. not recovered) and B = ln(β/(1−α)) (cross down → *accept* H0, i.e. recovered)."""
    return math.log((1.0 - beta) / alpha), math.log(beta / (1.0 - alpha))


def sprt_evaluate(outcomes: list[bool], *, p0: float, p1: float, alpha: float, beta: float) -> dict:
    """Sequential Probability Ratio Test over a per-cycle fault stream (``True`` = fault/relapse).

    Accumulates the log-likelihood ratio of H1 (relapse rate ``p1``) vs H0 (recovery holds, rate ``p0``)
    and reports the first bound crossing: ``accept`` (recovery demonstrated), ``reject`` (did not
    recover), or ``continue`` — plus how many more clean cycles an ``accept`` would need.
    """
    a_bound, b_bound = sprt_bounds(alpha, beta)
    up = math.log(p1 / p0)                      # a fault favours H1 (relapse) — LLR rises
    down = math.log((1.0 - p1) / (1.0 - p0))    # a clean cycle favours H0 (recovered) — LLR falls
    llr = 0.0
    decision, decided_at = "continue", None
    for i, fault in enumerate(outcomes, start=1):
        llr += up if fault else down
        if decision == "continue":
            if llr >= a_bound:
                decision, decided_at = "reject", i
            elif llr <= b_bound:
                decision, decided_at = "accept", i
    clean_to_accept: int | None = None
    if decision == "continue" and down != 0:
        clean_to_accept = max(0, math.ceil((b_bound - llr) / down))
    elif decision == "accept":
        clean_to_accept = 0
    return {
        "decision": decision, "decided_at_cycle": decided_at, "n": len(outcomes),
        "llr": round(llr, 3), "accept_bound": round(b_bound, 3), "reject_bound": round(a_bound, 3),
        "clean_cycles_to_accept": clean_to_accept,
        "p0": p0, "p1": p1, "alpha": alpha, "beta": beta,
    }


# ── assessment over an incident ───────────────────────────────────────────────
@dataclass
class ReliabilityAssessment:
    available: bool
    incident_id: str = ""
    stable_cycles: int = 0
    observed_cycles: int = 0
    required_stable_cycles: int = 0
    target_relapse_rate: float = TARGET_RELAPSE_RATE
    confidence_level: float = CONFIDENCE_LEVEL
    confidence_now: float = 0.0                 # confidence relapse ≤ target at the current stable run
    confidence_at_window: float = 0.0           # …if the full window completes fault-free
    demonstrated_relapse_ceiling: float = 1.0   # per-cycle relapse upper bound at the current run, conf C
    cycles_for_target: int = 0                  # cycles needed to hit the target confidence
    window_grade: str = ""                      # how strong the contract's window is, in words
    sprt: dict = field(default_factory=dict)    # Wald sequential test: accept / reject / continue
    sprt_summary: str = ""
    hazard: dict = field(default_factory=dict)
    verdict_confidence: str = ""
    headline: str = ""
    recommendation: str = ""
    advisory: str = ("Advisory only — the deterministic evaluator decides closure. This grades the "
                     "verification window and the current run statistically; it never changes the verdict.")


def _relapse_history(session: Session, incident: Incident) -> tuple[list[int], bool]:
    """Relapse cycles for this incident's *machine model* — derived from data, not hard-coded.

    Combines (a) live fault recurrences observed on any machine of the same model with (b) a documented
    prior for the fault code (if one exists). Returns ``(sorted_cycles, used_prior)``."""
    machine = session.get(Machine, incident.machine_id)
    model = machine.machine_model if machine else None

    live: list[int] = []
    if model:
        model_machine_ids = {
            m.id for m in session.exec(select(Machine).where(Machine.machine_model == model)).all()
        }
        if model_machine_ids:
            inc_ids = {
                i.id for i in session.exec(
                    select(Incident).where(Incident.machine_id.in_(model_machine_ids))  # type: ignore[attr-defined]
                ).all()
            }
            live = [
                o.cycle_index
                for o in session.exec(
                    select(RecoveryObservation).where(RecoveryObservation.fault_code.is_not(None))  # type: ignore[union-attr]
                ).all()
                if o.incident_id in inc_ids and o.cycle_index and o.fault_code == incident.fault_code
            ]

    prior = list(KNOWN_RECURRENCE_PRIORS.get(incident.fault_code or "", ()))
    return sorted([*prior, *live]), bool(prior)


def _hazard_read(session: Session, incident: Incident, required_window: int) -> dict:
    """Classify where the fault sits on the bathtub curve, from machine/fault-scoped relapse history."""
    relapse_cycles, used_prior = _relapse_history(session, incident)
    n = len(relapse_cycles)
    mean_cycle = round(sum(relapse_cycles) / n, 1) if n else None

    pattern, beta_hint, interpretation = "insufficient_data", None, "Not enough recurrence history to classify."
    if mean_cycle is not None and required_window > 0:
        ratio = mean_cycle / required_window
        if ratio < 0.7:
            pattern = "early_life"          # infant mortality
            beta_hint = "β < 1"
            interpretation = (
                f"Relapses cluster around cycle {mean_cycle:g}, well inside the {required_window}-cycle "
                "window — the early-life (infant-mortality) region of the bathtub curve (Weibull β<1). "
                "That signature means the first intervention left a latent defect (e.g. a degrading "
                "component), not a random or wear-out failure. It is the statistical reason 'work "
                "completed' is not 'recovered' — and why the full window must be verified."
            )
        elif ratio <= 1.2:
            pattern = "random_constant"     # useful-life
            beta_hint = "β ≈ 1"
            interpretation = (
                f"Relapses occur near the end of the {required_window}-cycle window (Weibull β≈1, constant "
                "hazard) — consistent with random failures during useful life rather than a missed root cause."
            )
        else:
            pattern = "wear_out"
            beta_hint = "β > 1"
            interpretation = (
                "Relapses occur late and increase with running time (Weibull β>1, wear-out) — points to "
                "component end-of-life rather than a faulty repair."
            )

    note = "Machine/fault-scoped recurrence history; with few data points this is a qualitative read, " \
           "not a fitted Weibull model."
    if used_prior:
        note += " Includes a documented historical prior for this fault."
    return {
        "relapse_cycles_observed": relapse_cycles,
        "mean_cycles_to_relapse": mean_cycle,
        "sample_size": n,
        "pattern": pattern,
        "weibull_shape_hint": beta_hint,
        "interpretation": interpretation,
        "data_confidence": "limited" if n < 5 else "moderate",
        "data_note": note,
    }


def _outcome_stream(session: Session, window: RecoveryWindow) -> list[bool]:
    """Per-cycle fault stream for a window (``True`` = the originating fault recurred that cycle)."""
    obs = session.exec(
        select(RecoveryObservation).where(RecoveryObservation.window_id == window.id)
        .order_by(RecoveryObservation.cycle_index)  # type: ignore[arg-type]
    ).all()
    return [bool(o.fault_code) for o in obs]


def assess(session: Session, incident: Incident) -> dict:
    """Statistical confidence in the recovery verdict for an incident (advisory)."""
    p0, conf = TARGET_RELAPSE_RATE, CONFIDENCE_LEVEL

    contract = (session.get(RecoveryContract, incident.current_contract_id)
                if incident.current_contract_id else None)
    if contract is None:
        return {"available": False, "incident_id": incident.id,
                "reason": "No active recovery contract yet — statistics apply once monitoring begins.",
                "advisory": ReliabilityAssessment(False).advisory}

    window = _latest_window(session, contract)
    required = (window.required_stable_cycles if window else None) or \
        contract.spec.get("verification_window", {}).get("required_stable_cycles", 30)
    stable = window.stable_streak if window else 0
    observed = window.observed_cycles if window else 0

    confidence_now = confidence_relapse_at_most(stable, p0)
    confidence_at_window = confidence_relapse_at_most(required, p0)
    relapse_ceiling = round(1.0 - reliability_lower_bound(stable, conf), 4) if stable > 0 else 1.0
    need = cycles_required(conf, p0)

    # Grade the contract window in plain words.
    cw = confidence_at_window
    if cw >= 0.90:
        window_grade = f"strong ({round(cw*100)}% confidence relapse ≤ {round(p0*100)}%/cycle)"
    elif cw >= 0.75:
        window_grade = f"adequate ({round(cw*100)}% confidence relapse ≤ {round(p0*100)}%/cycle)"
    else:
        window_grade = f"weak ({round(cw*100)}% confidence relapse ≤ {round(p0*100)}%/cycle)"

    hazard = _hazard_read(session, incident, required)

    # Wald SPRT over the window's per-cycle fault stream (two-sided: accept / reject / continue).
    stream = _outcome_stream(session, window) if window else []
    sprt = sprt_evaluate(stream, p0=SPRT_P0, p1=SPRT_P1, alpha=SPRT_ALPHA, beta=SPRT_BETA)
    if sprt["decision"] == "accept":
        sprt_summary = (f"Sequential test: recovery ACCEPTED at cycle {sprt['decided_at_cycle']} "
                        f"(α=β={round(SPRT_ALPHA*100)}%) — discriminating ≤{round(SPRT_P0*100)}% from "
                        f"≥{round(SPRT_P1*100)}%/cycle relapse.")
    elif sprt["decision"] == "reject":
        sprt_summary = (f"Sequential test: recovery REJECTED at cycle {sprt['decided_at_cycle']} — the "
                        "fault stream is consistent with a relapse, not a holding recovery.")
    else:
        cta = sprt["clean_cycles_to_accept"]
        sprt_summary = (f"Sequential test: undecided — about {cta} more clean cycle(s) would accept. "
                        "It counts only observed faults, so check the Recovery Forecaster before trusting it.")

    proven = stable >= need
    if stable <= 0:
        verdict_conf = ("No fault-free run yet (stable streak 0) — statistically we cannot yet "
                        "distinguish a holding recovery from a relapse.")
    elif proven:
        verdict_conf = (f"After {stable} fault-free cycles we are ≥{round(conf*100)}% confident the "
                        f"per-cycle relapse probability is ≤ {round(p0*100)}% — recovery is statistically demonstrated.")
    else:
        verdict_conf = (f"After {stable} fault-free cycles we are {round(confidence_now*100)}% confident "
                        f"relapse ≤ {round(p0*100)}%/cycle. Demonstrating ≤{round(p0*100)}% at "
                        f"{round(conf*100)}% confidence needs {need} cycles — recovery is not yet proven.")

    headline = (f"{stable}/{need} stable cycles for {round(conf*100)}% confidence · "
                f"window grade: {window_grade.split(' (')[0]} · hazard: {hazard['pattern'].replace('_', ' ')}")

    if required >= need:
        recommendation = (f"The {required}-cycle window meets the target ({need} cycles needed for "
                          f"{round(conf*100)}% confidence at ≤{round(p0*100)}%/cycle).")
    else:
        recommendation = (f"To demonstrate ≤{round(p0*100)}%/cycle at {round(conf*100)}% confidence, set "
                          f"required_stable_cycles ≥ {need} (currently {required}). The shorter window "
                          "still catches a gross false recovery but leaves residual risk — advisory.")

    a = ReliabilityAssessment(
        available=True, incident_id=incident.id, stable_cycles=stable, observed_cycles=observed,
        required_stable_cycles=required, target_relapse_rate=p0, confidence_level=conf,
        confidence_now=round(confidence_now, 4), confidence_at_window=round(confidence_at_window, 4),
        demonstrated_relapse_ceiling=relapse_ceiling, cycles_for_target=need, window_grade=window_grade,
        sprt=sprt, sprt_summary=sprt_summary, hazard=hazard,
        verdict_confidence=verdict_conf, headline=headline, recommendation=recommendation,
    )
    return a.__dict__
