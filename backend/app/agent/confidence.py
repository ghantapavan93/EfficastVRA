"""Recovery confidence — a deliberately cautious *heuristic* display aid (NOT a calibrated probability).

It is a hand-tuned function of the deterministic verdict + stable-streak progress that never reads as
"victory" while the verification window is still open, because the entire product thesis — and the
τ-bench / "illusions of reflection" findings (docs/AGENT_RESEARCH.md) — is that early post-intervention
signals are not proof. It is a display aid only and is uncalibrated; closure is decided by the
deterministic evaluator, never by this number. (See docs/SYSTEM_OVERVIEW.md on the analytics honesty.)
"""

from __future__ import annotations

from app.services.evaluator import EvaluationResult


def recovery_confidence(result: EvaluationResult) -> float:
    """0..1 confidence that the *recovery itself* will hold, given the current evaluation."""
    if result.verdict == "verified":
        return 0.97
    if result.verdict == "violated":
        return 0.05
    if result.verdict == "insufficient_evidence":
        return 0.15
    # monitoring: rise with the stable streak but stay capped — cautious by design.
    req = result.required_stable_cycles or 30
    frac = (result.stable_streak / req) if req else 0.0
    if result.awaiting_quality:  # technically passed, gated only on a human quality release
        return 0.85
    return round(min(0.80, 0.30 + 0.45 * frac), 2)


def confidence_label(c: float) -> str:
    if c >= 0.95:
        return "verified"
    if c >= 0.75:
        return "high"
    if c >= 0.45:
        return "moderate"
    if c >= 0.15:
        return "cautious"
    return "low"
