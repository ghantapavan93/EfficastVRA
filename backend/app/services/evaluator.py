"""The deterministic Recovery Contract evaluator.

Given a contract's normalised conditions + the observations in its active verification window +
human/quality evidence, it computes each condition's status and an overall verdict. **No LLM is
involved.** The model may explain a verdict; only this code produces one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlmodel import Session, select

from app.domain.base import utcnow
from app.domain.enums import CompareOp, ConditionKind, ConditionStatus
from app.domain.models import (
    EvidenceRequirement,
    RecoveryCondition,
    RecoveryContract,
    RecoveryObservation,
)
from app.services.evidence import requirement_satisfied
from app.services.quality import quality_release_satisfied
from app.services.windows import get_active_window

CS = ConditionStatus


@dataclass
class EvaluationResult:
    verdict: str  # monitoring | violated | verified | insufficient_evidence
    summary: str
    observed_cycles: int = 0
    stable_streak: int = 0
    required_stable_cycles: int = 0
    technical_pass: bool = False
    awaiting_quality: bool = False
    violated_keys: list[str] = field(default_factory=list)
    blocked_keys: list[str] = field(default_factory=list)
    conditions: list[dict] = field(default_factory=list)


def _cycle_seconds(contract: RecoveryContract) -> float:
    return float((contract.verification_window or {}).get("cycle_seconds", 12.2)) or 12.2


def _deadline_cycles(cond: RecoveryCondition, contract: RecoveryContract) -> Optional[int]:
    if cond.deadline_value is None:
        return None
    if cond.deadline_kind == "cycles":
        return int(cond.deadline_value)
    if cond.deadline_kind == "minutes":
        return int((cond.deadline_value * 60.0) / _cycle_seconds(contract))
    return None


def is_stable_observation(obs: RecoveryObservation, conditions: list[RecoveryCondition]) -> bool:
    """A cycle is 'stable' iff it satisfies every continuous machine/production condition and has no
    fault recurrence. Used to count consecutive stable cycles."""
    # ANY active fault makes a cycle non-stable — "30 stable cycles" must mean genuinely fault-free, not
    # merely free of the one originating fault. A new/secondary fault during the window (a real risk on
    # physical equipment) must reset the streak, even if the contract's NOT_RECUR names a different code.
    if obs.fault_code:
        return False
    for c in conditions:
        if c.kind == ConditionKind.QUALITY:
            continue
        if c.op == CompareOp.LTE and obs.vibration is not None and c.key == "vibration_rms":
            if obs.vibration > (c.threshold or 0):
                return False
        elif c.op == CompareOp.WITHIN_PCT and c.key == "cycle_time" and obs.cycle_time is not None:
            base = c.baseline or 0
            if base and abs(obs.cycle_time - base) / base > (c.threshold or 0):
                return False
        elif c.op == CompareOp.LT and c.key == "scrap" and obs.scrap_pct is not None:
            if obs.scrap_pct >= (c.threshold or 0):
                return False
        elif c.op == CompareOp.NOT_RECUR and obs.fault_code and obs.fault_code == c.fault_code:
            return False
    return True


def _evaluate_condition(
    session: Session,
    cond: RecoveryCondition,
    contract: RecoveryContract,
    observations: list[RecoveryObservation],
    window_stable: int,
    window_required: int,
    window_complete: bool,
) -> tuple[ConditionStatus, Optional[float]]:
    obs = observations
    latest = obs[-1] if obs else None
    observed = len(obs)

    # Quality conditions are satisfied by validated evidence, not telemetry.
    if cond.kind == ConditionKind.QUALITY:
        req = session.exec(
            select(EvidenceRequirement)
            .where(EvidenceRequirement.contract_id == contract.id)
            .where(EvidenceRequirement.condition_id == cond.id)
        ).first()
        if req is None:
            # fall back: any requirement that blocks this condition key
            reqs = session.exec(
                select(EvidenceRequirement).where(EvidenceRequirement.contract_id == contract.id)
            ).all()
            req = next((r for r in reqs if cond.key in (r.blocks_conditions or [])), None)
        if req is not None and requirement_satisfied(session, req):
            return CS.PASSED, 1.0
        return CS.BLOCKED, None

    if cond.op == CompareOp.NOT_RECUR:
        hits = [o for o in obs if o.fault_code and o.fault_code == cond.fault_code]
        if hits:
            return CS.VIOLATED, float(len(hits))
        if window_complete:
            return CS.PASSED, 0.0
        return (CS.PASSING if obs else CS.PENDING), 0.0

    if cond.op == CompareOp.DECLINING:
        if len(obs) < 2 or latest is None:
            return CS.PENDING, (latest.temperature if latest else None)
        declining = obs[-1].temperature is not None and obs[0].temperature is not None and \
            obs[-1].temperature < obs[0].temperature
        deadline = _deadline_cycles(cond, contract)
        if deadline is not None and observed >= deadline and not declining:
            return CS.VIOLATED, latest.temperature
        if declining:
            return (CS.PASSED if window_complete else CS.PASSING), latest.temperature
        return CS.PENDING, latest.temperature

    if cond.op == CompareOp.COUNT_GTE:  # stable_cycles
        cur = float(window_stable)
        if window_stable >= int(cond.threshold or window_required):
            return CS.PASSED, cur
        return (CS.PASSING if window_stable > 0 else CS.PENDING), cur

    # Scalar comparisons on the latest reading
    value = None
    if latest is not None:
        value = {
            "vibration_rms": latest.vibration,
            "cycle_time": latest.cycle_time,
            "scrap": latest.scrap_pct,
        }.get(cond.key)
    if value is None:
        return CS.BLOCKED, None

    if cond.op == CompareOp.WITHIN_PCT:
        base = cond.baseline or 0
        passing = bool(base) and abs(value - base) / base <= (cond.threshold or 0)
    elif cond.op == CompareOp.LTE:
        passing = value <= (cond.threshold or 0)
    elif cond.op == CompareOp.LT:
        passing = value < (cond.threshold or 0)
    elif cond.op == CompareOp.GTE:
        passing = value >= (cond.threshold or 0)
    elif cond.op == CompareOp.GT:
        passing = value > (cond.threshold or 0)
    else:
        passing = value == (cond.threshold or 0)

    deadline = _deadline_cycles(cond, contract)
    if deadline is not None and observed >= deadline:
        met_in_deadline = any(
            _scalar_for(o, cond.key) is not None and _passes(_scalar_for(o, cond.key), cond)
            for o in obs[:deadline]
        )
        if not met_in_deadline and not passing:
            return CS.VIOLATED, value
    if passing:
        return (CS.PASSED if window_complete else CS.PASSING), value
    return CS.PENDING, value


def _scalar_for(o: RecoveryObservation, key: str) -> Optional[float]:
    return {"vibration_rms": o.vibration, "cycle_time": o.cycle_time, "scrap": o.scrap_pct}.get(key)


def _passes(value: float, cond: RecoveryCondition) -> bool:
    if cond.op == CompareOp.LTE:
        return value <= (cond.threshold or 0)
    if cond.op == CompareOp.LT:
        return value < (cond.threshold or 0)
    if cond.op == CompareOp.WITHIN_PCT:
        base = cond.baseline or 0
        return bool(base) and abs(value - base) / base <= (cond.threshold or 0)
    return False


def evaluate(session: Session, contract: RecoveryContract) -> EvaluationResult:
    window = get_active_window(session, contract)
    observations = []
    stable = 0
    required = int((contract.verification_window or {}).get("required_stable_cycles", 30))
    if window is not None:
        observations = session.exec(
            select(RecoveryObservation)
            .where(RecoveryObservation.window_id == window.id)
            .order_by(RecoveryObservation.cycle_index)  # type: ignore[arg-type]
        ).all()
        stable = window.stable_streak
        required = window.required_stable_cycles
    window_complete = stable >= required

    conditions = session.exec(
        select(RecoveryCondition).where(RecoveryCondition.contract_id == contract.id)
    ).all()

    violated: list[str] = []
    blocked: list[str] = []
    cond_views: list[dict] = []
    for cond in conditions:
        status, value = _evaluate_condition(
            session, cond, contract, observations, stable, required, window_complete
        )
        cond.status = status
        cond.current_value = value
        cond.evaluated_at = utcnow()
        session.add(cond)
        if status == CS.VIOLATED:
            violated.append(cond.key)
        if status == CS.BLOCKED and cond.kind != ConditionKind.QUALITY:
            blocked.append(cond.key)
        cond_views.append({
            "key": cond.key, "kind": cond.kind.value, "label": cond.label,
            "op": cond.op.value, "threshold": cond.threshold, "unit": cond.unit,
            "baseline": cond.baseline, "current_value": value, "status": status.value,
            "sensor_tag": cond.sensor_tag, "policy_ref": cond.policy_ref,
        })
    session.flush()

    # Technical pass: every machine/production condition PASSED + stable window met + first-piece PASSED.
    non_quality = [c for c in conditions if c.kind != ConditionKind.QUALITY]
    quality = [c for c in conditions if c.kind == ConditionKind.QUALITY]
    technical_pass = (
        bool(observations)
        and window_complete
        and all(c.status == CS.PASSED for c in non_quality)
        and all(c.status == CS.PASSED for c in quality)
    )
    q_ok, _q_reason = quality_release_satisfied(session, contract.id)

    if violated:
        verdict = "violated"
        summary = f"Recovery contract violated: {', '.join(violated)}."
    elif technical_pass and q_ok:
        verdict = "verified"
        summary = "All conditions passed for the full window and quality release is approved."
    elif technical_pass and not q_ok:
        verdict = "monitoring"
        summary = "All technical conditions met; awaiting quality release."
    else:
        verdict = "monitoring"
        summary = f"Monitoring: {stable}/{required} stable cycles."

    return EvaluationResult(
        verdict=verdict,
        summary=summary,
        observed_cycles=len(observations),
        stable_streak=stable,
        required_stable_cycles=required,
        technical_pass=technical_pass,
        awaiting_quality=technical_pass and not q_ok,
        violated_keys=violated,
        blocked_keys=blocked,
        conditions=cond_views,
    )
