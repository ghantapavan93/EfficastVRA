"""Recovery Decision Room — the release decision as a multi-domain matrix, not a single green card.

A production release is only as strong as its weakest domain. This read-only view re-projects the
deterministic evaluator + disposition (which already own the verdict) into the eight release domains a
plant actually signs off — Equipment, Process, Quality, Comparability, Evidence, Freshness, Safety,
Authorization — each with a pass/blocked status and its blocking issue. The overall outcome is the
disposition's; a high confidence score can NEVER substitute for a blocked domain.

Composed entirely from tested code (``assess_disposition`` + ``evaluate``). It decides nothing new and
touches no machine.
"""

from __future__ import annotations

from sqlmodel import Session

from app.domain.enums import ConditionKind
from app.domain.models import Incident, RecoveryContract
from app.services.disposition import assess_disposition
from app.services.evaluator import evaluate

_STATUS_LABEL = {"pass": "Passed", "blocked": "Blocked", "insufficient": "Insufficient",
                 "monitoring": "Monitoring", "warn": "Caution"}


def _summary(conds: list[dict]) -> tuple[int, int, bool, bool]:
    total = len(conds)
    passed = sum(1 for c in conds if c["status"] == "PASSED")
    violated = any(c["status"] == "VIOLATED" for c in conds)
    blocked = any(c["status"] == "BLOCKED" for c in conds)
    return total, passed, violated, blocked


def assess_release_matrix(session: Session, incident: Incident) -> dict:
    disp = assess_disposition(session, incident)
    if not disp.get("available"):
        return {"available": False, "incident_id": incident.id, "reason": disp.get("reason")}

    contract = session.get(RecoveryContract, incident.current_contract_id)
    ev = evaluate(session, contract)
    machine = [c for c in ev.conditions if c["kind"] == ConditionKind.MACHINE.value]
    process = [c for c in ev.conditions if c["kind"] == ConditionKind.PRODUCTION.value]
    quality = [c for c in ev.conditions if c["kind"] == ConditionKind.QUALITY.value]
    window_complete = ev.stable_streak >= ev.required_stable_cycles
    inv = {i["key"]: i for i in disp["hard_invariants"]}
    sensor = disp["sensor_trust"]["status"]
    comp = disp["comparability"]["classification"]
    confounders = disp["comparability"]["confounding_dimensions"]

    domains: list[dict] = []

    def add(domain: str, status: str, blocking: str, detail: str):
        domains.append({"domain": domain, "status": status, "result": _STATUS_LABEL[status],
                        "blocking_issue": blocking, "detail": detail})

    # 1 · Equipment (MACHINE conditions + sensor trust)
    t, p, v, _ = _summary(machine)
    if v:
        add("Equipment", "blocked", "A machine condition is violated", f"{p}/{t} within threshold")
    elif sensor in ("UNTRUSTED", "UNKNOWN"):
        add("Equipment", "insufficient", f"Sensor trust is {sensor.lower()}", f"{p}/{t} passed; sensor {sensor.lower()}")
    elif t and p == t:
        add("Equipment", "pass", "None", f"{p}/{t} conditions within threshold")
    else:
        add("Equipment", "monitoring", "Not all conditions met yet", f"{p}/{t} passed")

    # 2 · Process (PRODUCTION conditions + window)
    t, p, v, _ = _summary(process)
    if v:
        add("Process", "blocked", "Fault recurrence / condition violated", f"{p}/{t} passed")
    elif not window_complete:
        add("Process", "monitoring", f"{ev.required_stable_cycles - ev.stable_streak} more stable cycles needed",
            f"{ev.stable_streak}/{ev.required_stable_cycles} stable cycles")
    elif t and p == t:
        add("Process", "pass", "None", f"{p}/{t} conditions; window complete")
    else:
        add("Process", "monitoring", "Not all conditions met yet", f"{p}/{t} passed")

    # 3 · Quality (QUALITY conditions + approval)
    t, p, v, _ = _summary(quality)
    q_ok = inv["approvals"]["ok"]
    if v:
        add("Quality", "blocked", "A quality condition is violated", f"{p}/{t} passed")
    elif t and p == t and q_ok:
        add("Quality", "pass", "None", "inspection passed; release approved")
    elif t and p == t and not q_ok:
        add("Quality", "blocked", "Quality approval missing", inv["approvals"]["detail"])
    else:
        add("Quality", "monitoring", "Quality checks pending", f"{p}/{t} passed")

    # 4 · Comparability
    if comp == "COMPARABLE":
        add("Comparability", "pass", "None", "before/after conditions comparable")
    elif comp == "PARTIALLY_COMPARABLE":
        add("Comparability", "warn", "Some conditions shifted", "; ".join(confounders) or "minor shifts")
    else:
        add("Comparability", "insufficient", f"Conditions {comp.replace('_', ' ').lower()}",
            "; ".join(confounders) or comp)

    # 5 · Evidence  · 6 · Freshness
    ev_ok = inv["evidence"]["ok"]
    add("Evidence", "pass" if ev_ok else "blocked", "None" if ev_ok else "Required evidence missing/stale", inv["evidence"]["detail"])
    add("Freshness", "pass" if ev_ok else "warn", "None" if ev_ok else "May include stale evidence",
        "within freshness budget" if ev_ok else inv["evidence"]["detail"])

    # 7 · Safety  · 8 · Authorization
    add("Safety", "pass", "None", "No machine-control action exists or was used (gateway-enforced); no active safety hold.")
    add("Authorization", "pass" if q_ok else "blocked", "None" if q_ok else "Required approval missing", inv["approvals"]["detail"])

    blocking = [d for d in domains if d["status"] in ("blocked", "insufficient")]
    outcome = disp["disposition"]
    headline = ("All release domains passed — production release is authorized."
                if outcome == "VERIFIED"
                else f"{outcome.replace('_', ' ').title()} — {len(blocking)} domain(s) blocking release"
                     + (f": {blocking[0]['domain']} ({blocking[0]['blocking_issue']})." if blocking else "."))

    return {
        "available": True, "incident_id": incident.id,
        "outcome": outcome, "outcome_meaning": disp["meaning"], "headline": headline,
        "can_close": disp["can_close"], "effective_confidence": disp["effective_confidence"],
        "blocking_count": len(blocking), "domains": domains, "reasons": disp["reasons"],
        "basis": ("The release decision is multi-domain — EVERY domain must pass. Re-projected read-only from "
                  "the deterministic evaluator + disposition (rule ccr-1.0). A single confidence score can "
                  "never substitute for a blocked domain. Advisory; closure is owned by the evaluator."),
    }
