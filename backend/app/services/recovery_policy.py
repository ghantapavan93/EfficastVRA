"""The comparable-conditions recovery CEILING — one canonical policy, applied everywhere.

A single function decides how strongly the system may represent recovery, given the raw signature
confidence and the Comparable-Conditions verdict. Two unbreakable rules:

1. **It can only LOWER confidence, never raise it.** Comparability is a ceiling, not a booster.
2. **It never overrides a hard requirement.** A violated condition / relapse stays FAILED; a missing
   quality / evidence / approval / freshness gate stays INSUFFICIENT — regardless of how comparable the
   conditions are. The deterministic evaluator still owns the hard gate; this composes comparability on top.

Invariant (rule ``ccr-1.0``): nothing — signature ladder, disposition, certificate, false-closure-risk,
API, or UI — may represent high-confidence **VERIFIED** recovery when comparability is **NOT_COMPARABLE**
or **UNKNOWN**. UNKNOWN is *default-deny* (absence of captured context is not evidence of comparability).

Pure: takes primitives, touches no DB. Call sites pass in the comparability verdict (from
``services/comparable_conditions.py``) and the evaluator's hard-gate state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

RULE_VERSION = "ccr-1.0"

# signature causal-confidence ladder, weakest → strongest
_LADDER = ["insufficient_evidence", "recovery_observed", "consistent_with_intervention", "strongly_consistent"]
_RANK = {r: i for i, r in enumerate(_LADDER)}

# the highest ladder rung each comparability class permits
_CEILING = {
    "COMPARABLE": "strongly_consistent",
    "PARTIALLY_COMPARABLE": "consistent_with_intervention",
    "NOT_COMPARABLE": "insufficient_evidence",
    "UNKNOWN": "insufficient_evidence",
}
_MULT_DEFAULT = {"COMPARABLE": 1.0, "PARTIALLY_COMPARABLE": 0.6, "NOT_COMPARABLE": 0.2, "UNKNOWN": 0.5}

# evidence_status — the deterministic hard-gate state the evaluator already decided
ELIGIBLE = "ELIGIBLE"          # every hard condition / quality / evidence / window requirement passed
INSUFFICIENT = "INSUFFICIENT"  # a hard gate is unmet (missing/stale evidence, no quality release, short window)
FAILED = "FAILED"              # a hard condition was violated / the originating fault relapsed


def cap_rung(rung: str, comparability: str) -> str:
    """Lower ``rung`` to the ceiling the comparability class permits (never raises it)."""
    ceiling = _CEILING.get((comparability or "UNKNOWN").upper(), "insufficient_evidence")
    if rung not in _RANK:
        return ceiling
    return rung if _RANK[rung] <= _RANK[ceiling] else ceiling


@dataclass
class EffectiveConfidence:
    raw_confidence: float
    comparability: str
    comparability_multiplier: float
    effective_confidence: float
    policy_result: str            # VERIFIED | INSUFFICIENT_EVIDENCE | FAILED
    confidence_tier: str          # NORMAL | REDUCED | NONE
    capped_rung: str              # ladder-rung ceiling permitted
    causal_language_allowed: bool
    confounding_dimensions: list = field(default_factory=list)
    rule_version: str = RULE_VERSION
    notes: list = field(default_factory=list)

    def as_provenance(self) -> dict:
        """The 7 fields the invariant requires recorded wherever a recovery confidence is represented."""
        return {
            "raw_confidence": round(self.raw_confidence, 3),
            "comparability_classification": self.comparability,
            "comparability_multiplier": round(self.comparability_multiplier, 3),
            "effective_confidence": round(self.effective_confidence, 3),
            "confounding_dimensions": self.confounding_dimensions,
            "policy_result": self.policy_result,
            "rule_version": self.rule_version,
        }


def derive_effective_recovery_confidence(
    raw_signature_confidence: float,
    comparability_result: str,
    comparability_multiplier: float,
    evidence_status: str,
    *,
    confounders: list | None = None,
) -> EffectiveConfidence:
    """The canonical ceiling. See module docstring for the invariant."""
    comparability = (comparability_result or "UNKNOWN").upper()
    ceiling = _CEILING.get(comparability, "insufficient_evidence")
    confounders = list(confounders or [])
    raw = float(raw_signature_confidence or 0.0)
    mult = float(comparability_multiplier if comparability_multiplier is not None
                 else _MULT_DEFAULT.get(comparability, 0.5))

    # 1. hard requirements dominate — a confidence score / comparability multiplier can never override them.
    if evidence_status == FAILED:
        return EffectiveConfidence(
            raw, comparability, mult, 0.0, "FAILED", "NONE", "insufficient_evidence", False,
            confounders, RULE_VERSION,
            ["A hard recovery condition was violated (relapse) — comparability cannot hide a directly "
             "observed failure."])
    if evidence_status == INSUFFICIENT:
        return EffectiveConfidence(
            raw, comparability, mult, round(raw * mult, 3), "INSUFFICIENT_EVIDENCE", "NONE",
            cap_rung("recovery_observed", comparability), False, confounders, RULE_VERSION,
            ["A hard gate (quality / evidence / approval / freshness / window) is unmet — not overridden by "
             "any confidence or comparability score."])

    # 2. evidence-eligible (the evaluator's hard gate passed): apply the comparability ceiling.
    if comparability == "COMPARABLE":
        return EffectiveConfidence(
            raw, comparability, 1.0, raw, "VERIFIED", "NORMAL", "strongly_consistent", True, [],
            RULE_VERSION, ["Comparable conditions — normal recovery evaluation."])
    if comparability == "PARTIALLY_COMPARABLE":
        return EffectiveConfidence(
            raw, comparability, mult, round(raw * mult, 3), "VERIFIED", "REDUCED",
            "consistent_with_intervention", True, confounders, RULE_VERSION,
            ["Partially comparable — effective confidence reduced and strong causal language withheld; "
             f"confounders: {', '.join(confounders) or 'unspecified'}."])
    # NOT_COMPARABLE or UNKNOWN → force INSUFFICIENT_EVIDENCE; never VERIFIED. UNKNOWN is default-deny.
    note = ("Operating conditions were not comparable — the improvement cannot be attributed to the "
            "intervention; forced to INSUFFICIENT_EVIDENCE." if comparability == "NOT_COMPARABLE"
            else "Operating context was not captured — default-deny: INSUFFICIENT_EVIDENCE until the "
                 "required context is available.")
    return EffectiveConfidence(
        raw, comparability, mult, round(raw * mult, 3), "INSUFFICIENT_EVIDENCE", "NONE",
        "insufficient_evidence", False, confounders, RULE_VERSION, [note])


def confounders_of(comparability: dict) -> list:
    """Helper: the labels of the dimensions that shifted (key/minor) in a comparability result."""
    return [d.get("label", d.get("key")) for d in (comparability.get("dimensions") or [])
            if d.get("status") == "shift" and d.get("weight") in ("key", "minor")]
