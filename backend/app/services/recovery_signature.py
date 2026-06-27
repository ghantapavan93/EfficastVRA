"""Expected Recovery Signature — advisory intervention-consistency assessment (read-only).

This is **NOT** the closure verdict and **NOT** a causal proof. The deterministic evaluator
(`services/evaluator.py`) solely owns closure. This layer answers a strictly weaker, explicitly hedged
question: *is the post-intervention trajectory CONSISTENT WITH the hypothesis that THIS intervention
caused the recovery — rather than with temporary symptom suppression, regression to the mean, changed
operating conditions, or noise?*

The **expected signature is derived from the contract's own conditions** — each ``CompareOp`` implies an
expected signal direction, each deadline implies a speed — plus the monitored degradation precursor. So
it is machine-agnostic (no F27/bearing literals; it works for any profile's conditions). Scoring yields
an ``alignment`` in [-1, 1] and a rung on an intervention-consistency ladder.

Two mandatory honesty caps keep it from overclaiming:
- **conditions-unverified** — operating conditions (load/product/speed/shift) are not captured in the
  data yet, so a changed-conditions confound can never be fully ruled out; the top rung always carries
  this caveat.
- **precursor-rising** — a climbing degradation precursor caps the rung below the top, even if the
  headline metrics and the sequential test would accept (it wires the forecaster's warning into the read).

Advisory + read-only: never mutates state, never decides closure, never imports the gateway.
Research: docs/CAUSAL_RECOVERY_RESEARCH.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import ceil
from typing import Optional

from sqlmodel import Session, select

from app.domain.base import utcnow
from app.domain.enums import CompareOp, ConditionKind
from app.domain.models import (
    Incident,
    RecoveryCondition,
    RecoveryContract,
    RecoveryObservation,
    RecoveryWindow,
)
from app.services.evaluator import _passes, signal_value

# ── intervention-consistency ladder (advisory; never the closure verdict, never "proof") ──────────────
INSUFFICIENT_EVIDENCE = "insufficient_evidence"
RECOVERY_OBSERVED = "recovery_observed"               # metrics improved, but attribution is weak
CONSISTENT_WITH_INTERVENTION = "consistent_with_intervention"
STRONGLY_CONSISTENT = "strongly_consistent"           # always carries the conditions-unverified caveat

LADDER = [INSUFFICIENT_EVIDENCE, RECOVERY_OBSERVED, CONSISTENT_WITH_INTERVENTION, STRONGLY_CONSISTENT]

# Per-signal weights — the degradation precursor dominates because it is the *leading* indicator: it
# warns of a latent relapse *before* the fault recurs, when every headline metric still looks in-spec.
# Fault recurrence (when present) and the precursor thus outrank the headline metrics, so the signature
# isn't fooled by "everything looks fine" during a latent failure. These weights are PROTOTYPE_ASSUMPTIONs
# tuned against the calibration harness (test_calibration.py) — env-tunable later.
_W_SCALAR = 0.5
_W_DECLINING = 0.5
_W_NOT_RECUR = 1.0
_W_PRECURSOR = 3.5
_TAU_ALIGN = 0.6              # alignment >= this ⇒ the observed trajectory "aligns" with the signature
_PRECURSOR_RISE_TOL = 0.05   # precursor trend above this over the window counts as "rising"
_PRECURSOR_GRADE_SPAN = 0.2  # rise (beyond the tolerance) that drives precursor agreement from +1 to -1
PRECURSOR_KEY = "bearing_precursor"   # the monitored degradation precursor channel (MVP: bearing)


@dataclass
class SignatureResult:
    rung: str
    alignment: float                       # weighted match of observed trajectory vs expected, [-1, 1]
    signals: list[dict] = field(default_factory=list)   # per-signal expectation + agreement
    caveats: list[str] = field(default_factory=list)
    conditions_matched: str = "UNKNOWN"    # the Comparable-Conditions verdict (populated by the live wrapper)
    observed_cycles: int = 0
    basis: str = ""
    # comparable-conditions ceiling (rule ccr-1.0) — populated by score_signature (the live path)
    effective_confidence: float = 0.0
    confounding_dimensions: list = field(default_factory=list)
    rule_version: str = ""


def _direction_for(op: CompareOp) -> Optional[str]:
    return {
        CompareOp.LTE: "down", CompareOp.LT: "down",
        CompareOp.GTE: "up", CompareOp.GT: "up",
        CompareOp.WITHIN_PCT: "converge", CompareOp.DECLINING: "down",
        CompareOp.NOT_RECUR: "absent",
    }.get(op)


def _weight_for(op: CompareOp) -> float:
    if op == CompareOp.NOT_RECUR:
        return _W_NOT_RECUR
    if op == CompareOp.DECLINING:
        return _W_DECLINING
    return _W_SCALAR


def expected_signature(conditions: list[RecoveryCondition]) -> list[dict]:
    """Derive the expected post-intervention response from the contract's own conditions (machine-agnostic:
    each CompareOp ⇒ a direction; each deadline ⇒ a speed), plus the monitored degradation precursor.
    Quality and stable-cycle (COUNT_GTE) conditions are not point-in-time trajectory signals — skipped."""
    sig: list[dict] = []
    for c in conditions:
        if c.kind == ConditionKind.QUALITY or c.op == CompareOp.COUNT_GTE:
            continue
        direction = _direction_for(c.op)
        if direction is None:
            continue
        sig.append({
            "signal": c.key,
            "direction": direction,
            "op": c.op.value,
            "fault_code": c.fault_code,
            "respond_by_cycle": c.deadline_value if c.deadline_kind == "cycles" else None,
            "weight": _weight_for(c.op),
        })
    # The genuinely novel bit: a real fix must not leave a monitored precursor rising. Declared generically
    # over "the precursor channel" so it attaches to whatever channel the active profile carries.
    sig.append({
        "signal": PRECURSOR_KEY, "direction": "flat_or_down", "op": "slope_lte",
        "fault_code": None, "respond_by_cycle": None, "weight": _W_PRECURSOR, "derived_precursor": True,
    })
    return sig


def _window_for(session: Session, contract: RecoveryContract) -> Optional[RecoveryWindow]:
    """The latest window for a contract, regardless of status (so a failed/superseded window scores too)."""
    return session.exec(
        select(RecoveryWindow)
        .where(RecoveryWindow.contract_id == contract.id)
        .order_by(RecoveryWindow.sequence.desc())  # type: ignore[attr-defined]
    ).first()


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _trailing_clean(observations: list[RecoveryObservation]) -> int:
    """Length of the trailing run of fault-free observations (a streak proxy when no window row exists)."""
    n = 0
    for o in reversed(observations):
        if o.fault_code:
            break
        n += 1
    return n


def score_observations(
    conditions: list[RecoveryCondition],
    observations: list[RecoveryObservation],
    *,
    required_stable: int,
    stable_streak: Optional[int] = None,
) -> SignatureResult:
    """Pure scoring core (no DB): score ``observations`` against the signature derived from ``conditions``.

    Shared by the live path (``score_signature``) and the calibration harness, so both compute the
    identical alignment. Deterministic and read-only."""
    sig = expected_signature(conditions)
    cond_by_key = {c.key: c for c in conditions}
    obs = observations
    observed = len(obs)

    fault_in_window = any(o.fault_code for o in obs)
    precursor_vals = [o.bearing_precursor for o in obs if o.bearing_precursor is not None]
    precursor_trend = (precursor_vals[-1] - precursor_vals[0]) if len(precursor_vals) >= 2 else None
    precursor_rising = precursor_trend is not None and precursor_trend > _PRECURSOR_RISE_TOL

    scored: list[dict] = []
    num = den = 0.0
    for s in sig:
        key = s["signal"]
        a: Optional[float] = None
        if s.get("derived_precursor"):
            if precursor_trend is not None:
                # Graded: flat/declining → +1; a clear rise → -1 (a real spread, not a binary cluster —
                # so the calibration harness can measure genuine reliability).
                a = _clamp(1.0 - max(0.0, precursor_trend - _PRECURSOR_RISE_TOL) / _PRECURSOR_GRADE_SPAN * 2.0)
        elif s["direction"] == "absent":                      # NOT_RECUR
            hits = any(o.fault_code and o.fault_code == s.get("fault_code") for o in obs)
            a = -1.0 if hits else 1.0
        elif s["op"] == CompareOp.DECLINING.value:            # trend condition
            temps = [v for v in (signal_value(o, key) for o in obs) if v is not None]
            if len(temps) >= 2:
                a = 1.0 if temps[-1] <= temps[0] else -1.0
        else:                                                  # scalar (LTE/LT/GTE/GT/WITHIN_PCT)
            cond = cond_by_key.get(key)
            judged = [
                _passes(v, cond)
                for v in (signal_value(o, key) for o in obs)
                if v is not None and cond is not None
            ]
            if judged:
                a = 2.0 * (sum(1 for j in judged if j) / len(judged)) - 1.0   # frac-in-spec → [-1, 1]
        scored.append({**s, "agreement": (round(a, 2) if a is not None else None)})
        if a is not None:
            num += s["weight"] * a
            den += s["weight"]

    alignment = round(num / den, 3) if den else 0.0

    need = required_stable or 30
    streak = stable_streak if stable_streak is not None else _trailing_clean(obs)
    c_min = observed >= max(3, ceil(need / 3))
    aligns = alignment >= _TAU_ALIGN
    persistence = streak >= need and not fault_in_window
    no_contradiction = (not fault_in_window) and (not precursor_rising)
    improved = any(s.get("agreement") is not None and s["agreement"] > 0 for s in scored)

    if not c_min:
        rung = INSUFFICIENT_EVIDENCE
    elif aligns and persistence and no_contradiction:
        rung = STRONGLY_CONSISTENT
    elif aligns:
        rung = CONSISTENT_WITH_INTERVENTION
    elif improved:
        rung = RECOVERY_OBSERVED
    else:
        rung = INSUFFICIENT_EVIDENCE

    caveats: list[str] = []
    # Honesty cap 1: operating conditions are never verified yet → the top rung must say so.
    if rung == STRONGLY_CONSISTENT:
        caveats.append("conditions-unverified: operating conditions (load/product/speed/shift) are not "
                       "captured, so a changed-conditions confound cannot be ruled out.")
    # Honesty cap 2: a rising precursor caps the rung below strongly-consistent.
    if precursor_rising and rung == STRONGLY_CONSISTENT:
        rung = CONSISTENT_WITH_INTERVENTION
        caveats.append("precursor-rising: the monitored degradation precursor is climbing — capped below "
                       "strongly-consistent (a relapse may be latent).")
    if fault_in_window:
        caveats.append("the originating fault recurred during the window — recovery is not consistent with "
                       "this intervention having fixed it.")

    basis = ("Advisory intervention-consistency only — NOT a causal proof and NOT the closure verdict "
             "(the deterministic evaluator owns closure). Alignment is a weighted match of the observed "
             "trajectory against the contract's own expected response; operating-conditions matching is "
             "unverified.")
    return SignatureResult(
        rung=rung, alignment=alignment, signals=scored, caveats=caveats,
        conditions_matched="UNKNOWN", observed_cycles=observed, basis=basis,
    )


def score_signature(
    session: Session, contract: RecoveryContract, *, as_of: Optional[datetime] = None
) -> SignatureResult:
    """Score the observed window of ``contract`` against its derived Expected Recovery Signature (live
    path). Read-only and advisory; never mutates state; never produces the closure verdict."""
    as_of = as_of or utcnow()  # accepted for symmetry with the evaluator; signature scoring is time-agnostic
    conditions = session.exec(
        select(RecoveryCondition).where(RecoveryCondition.contract_id == contract.id)
    ).all()
    win = _window_for(session, contract)
    if win is None:
        return SignatureResult(
            rung=INSUFFICIENT_EVIDENCE, alignment=0.0, signals=expected_signature(conditions),
            caveats=["no verification window yet — nothing to compare against the expected signature."],
            basis="Advisory only; no monitoring data.",
        )
    obs = session.exec(
        select(RecoveryObservation)
        .where(RecoveryObservation.window_id == win.id)
        .order_by(RecoveryObservation.cycle_index)  # type: ignore[arg-type]
    ).all()
    res = score_observations(
        conditions, obs, required_stable=win.required_stable_cycles or 30, stable_streak=win.stable_streak
    )
    return _apply_comparability_ceiling(session, contract, res)


def _apply_comparability_ceiling(
    session: Session, contract: RecoveryContract, res: SignatureResult
) -> SignatureResult:
    """Lower the causal-confidence rung to whatever the Comparable-Conditions verdict permits (rule ccr-1.0).
    This is the honest replacement for the previously-hardcoded ``conditions_matched = UNKNOWN`` — the
    signature may not claim a strong causal rung when the before/after weren't comparable. Read-only."""
    from app.services.comparable_conditions import assess_comparability
    from app.services.recovery_policy import (
        RULE_VERSION,
        cap_rung,
        confounders_of,
    )

    incident = session.get(Incident, contract.incident_id)
    comp = assess_comparability(session, incident) if incident else {"classification": "UNKNOWN"}
    classification = comp.get("classification", "UNKNOWN")
    capped = cap_rung(res.rung, classification)

    res.conditions_matched = classification
    res.confounding_dimensions = confounders_of(comp)
    res.effective_confidence = round(((res.alignment + 1.0) / 2.0) * (comp.get("confidence_multiplier") or 1.0), 3)
    res.rule_version = RULE_VERSION
    if classification == "COMPARABLE":
        # the comparability gate now positively verifies conditions → retire the standing generic disclaimer
        res.caveats = [c for c in res.caveats if "conditions-unverified" not in c]
        res.caveats.append("operating conditions verified COMPARABLE — the changed-conditions confound is "
                           "ruled out for the captured dimensions.")
    if capped != res.rung:
        res.caveats.append(
            f"comparable-conditions ceiling: capped from '{res.rung.replace('_', ' ')}' to "
            f"'{capped.replace('_', ' ')}' — operating conditions are {classification.replace('_', ' ').lower()}"
            + (f" (shifted: {', '.join(res.confounding_dimensions)})" if res.confounding_dimensions else "") + ".")
    res.rung = capped
    return res
