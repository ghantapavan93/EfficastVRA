"""Policy gates — small, explicit predicates over the deterministic evaluation."""

from __future__ import annotations

from app.domain.models import Incident, RecoveryContract
from app.services.evaluator import EvaluationResult


def should_reopen(contract: RecoveryContract, result: EvaluationResult) -> bool:
    policy = contract.reopening_policy or {}
    if result.verdict != "violated":
        return False
    # Fault-recurrence (NOT_RECUR) conditions are keyed ``fault_<code>`` by convention (see
    # RecoveryCondition.key), so this generalises to any machine/fault — not just the hero F27.
    fault_recurred = any(k.startswith("fault") for k in result.violated_keys)
    if fault_recurred and policy.get("reopen_on_fault_recurrence", True):
        return True
    return bool(policy.get("reopen_on_any_condition_violation", True))


def can_verify(result: EvaluationResult) -> bool:
    return result.verdict == "verified"


def should_escalate(incident: Incident, contract: RecoveryContract, result: EvaluationResult) -> bool:
    policy = contract.escalation_policy or {}
    return incident.reopened_count >= int(policy.get("escalate_after_failures", 2))
