"""Evidence Value Planner — what evidence would most reduce decision uncertainty, next?

Most systems say "evidence is missing." This ranks WHICH missing evidence would most improve the release
decision — by decision impact (does it unblock a hard gate?), effort, and an estimated confidence gain —
turning the agent from a passive analyzer into an active mission guide.

It still controls nothing and collects nothing: it reads the disposition + evaluator gaps and *recommends*.
Confidence-gain figures are PROTOTYPE_ASSUMPTION heuristics, not measured.
"""

from __future__ import annotations

from sqlmodel import Session

from app.domain.models import Incident, RecoveryContract
from app.services.disposition import assess_disposition
from app.services.evaluator import evaluate

_IMPACT_WEIGHT = {"Critical": 3, "High": 2, "Supporting": 1}


def plan_evidence(session: Session, incident: Incident) -> dict:
    disp = assess_disposition(session, incident)
    if not disp.get("available"):
        return {"available": False, "incident_id": incident.id, "reason": disp.get("reason")}

    contract = session.get(RecoveryContract, incident.current_contract_id)
    ev = evaluate(session, contract)
    inv = {i["key"]: i for i in disp["hard_invariants"]}
    recs: list[dict] = []

    def rec(title: str, impact: str, effort: str, gain: float, why: str):
        recs.append({"title": title, "decision_impact": impact, "effort": effort,
                     "confidence_gain": round(gain, 2), "why": why})

    if not inv["approvals"]["ok"]:
        rec("Obtain quality approval", "Critical", "Low", 0.18,
            "Unblocks the authorization gate — verification is prohibited without it.")
    if not inv["window"]["ok"]:
        remaining = max(0, ev.required_stable_cycles - ev.stable_streak)
        rec(f"Complete {remaining} additional comparable cycles", "High", "Medium", 0.11,
            "Completes the verification window so stability is proven across the full window, not assumed.")
    sensor = disp["sensor_trust"]["status"]
    if sensor in ("UNTRUSTED", "UNKNOWN"):
        rec("Validate or replace the affected sensor", "High", "Medium", 0.09,
            "A measurement we can't trust can't satisfy a hard recovery condition.")
    comp = disp["comparability"]["classification"]
    if comp != "COMPARABLE":
        conf = disp["comparability"]["confounding_dimensions"]
        rec("Re-verify under comparable conditions", "High", "Medium", 0.10,
            "Conditions " + comp.replace("_", " ").lower()
            + (f" (shifted: {', '.join(conf)})" if conf else "") + " — recovery can't yet be attributed to the intervention.")
        rec("Operator confirmation of operating conditions", "Supporting", "Low", 0.03,
            "Corroborates product / speed / load so partial comparability can be resolved.")
    for k in ev.blocked_keys:
        rec(f"Submit evidence: {k.replace('_', ' ')}", "High", "Medium", 0.08,
            "A required piece of evidence is missing or past its freshness budget.")
    if not inv["quality"]["ok"] and inv["window"]["ok"]:
        rec("Re-run the quality inspection", "High", "Medium", 0.07, "A quality condition is not yet satisfied.")

    # de-dup by title, rank by impact then estimated gain
    seen: set[str] = set()
    uniq: list[dict] = []
    for r in recs:
        if r["title"] in seen:
            continue
        seen.add(r["title"])
        uniq.append(r)
    uniq.sort(key=lambda r: (_IMPACT_WEIGHT[r["decision_impact"]], r["confidence_gain"]), reverse=True)
    uniq = uniq[:6]

    # Decision *readiness* (not raw signature alignment, which can be high while a hard gate is unmet):
    # fraction of hard invariants met, discounted by comparability + sensor trust.
    inv_total = max(1, len(disp["hard_invariants"]))
    inv_met = sum(1 for i in disp["hard_invariants"] if i["ok"])
    comp_factor = {"COMPARABLE": 1.0, "PARTIALLY_COMPARABLE": 0.85}.get(comp, 0.6)
    sensor_factor = 1.0 if sensor == "TRUSTED" else 0.8
    current = round((inv_met / inv_total) * comp_factor * sensor_factor, 2)
    potential = round(max(current, min(1.0, current + sum(r["confidence_gain"] for r in uniq))), 2)

    return {
        "available": True, "incident_id": incident.id, "outcome": disp["disposition"],
        "current_confidence": current, "potential_confidence": potential,
        "signature_confidence": disp.get("effective_confidence"),
        "unmet_invariants": sum(1 for d in disp["hard_invariants"] if not d["ok"]),
        "recommendations": uniq,
        "basis": ("Advisory ranking of which evidence would most reduce uncertainty. Confidence gains are "
                  "PROTOTYPE_ASSUMPTION heuristics; the agent recommends — it never collects evidence or "
                  "decides recovery (the deterministic evaluator does that)."),
    }
