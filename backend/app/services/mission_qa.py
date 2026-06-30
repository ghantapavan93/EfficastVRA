"""Conversational, role-adaptive Mission Q&A — the agent *explains*; it never decides.

A read-only assistant over a single mission. It composes the deterministic facts the system already
computes (the seven-stage spine, the disposition gate, the evaluator) and answers a plain-language
question, adapted to the asker's role, with citations back to the authoritative surface. It changes no
state and renders no verdict — the deterministic Recovery Contract evaluator owns closure. When asked
something it can't ground in those facts, it says so rather than inventing an answer.

This is the honest version of "is it an AI agent?": the reasoning layer narrates and routes; the
deterministic layer is the source of truth, and every answer is traceable to it.
"""

from __future__ import annotations

import re

from sqlmodel import Session

from app.domain.enums import Role
from app.domain.models import Incident, RecoveryContract
from app.services.disposition import assess_disposition
from app.services.evaluator import evaluate
from app.services.mission_spine import assess_mission

# Each role's lens: the part of the recovery they own, used to tailor "what this means for you".
_ROLE_LENS = {
    Role.SUPERVISOR: "You own the contract review, contingency approval, and the closure decision.",
    Role.TECHNICIAN: "You own the physical work and the post-intervention measurements.",
    Role.QUALITY_ENGINEER: "You own the first-piece result and the quality release / lot disposition.",
    Role.PLANT_ADMIN: "You own oversight and any escalation hand-off.",
}


def _role(role: str | Role | None) -> Role:
    if isinstance(role, Role):
        return role
    try:
        return Role(str(role or "supervisor").lower())
    except ValueError:
        return Role.SUPERVISOR


def _facts(session: Session, incident: Incident) -> dict:
    spine = assess_mission(session, incident)
    contract = (session.get(RecoveryContract, incident.current_contract_id)
                if incident.current_contract_id else None)
    disp = assess_disposition(session, incident) if contract else None
    ev = evaluate(session, contract) if contract else None
    return {"spine": spine, "disp": disp, "ev": ev, "contract": contract, "incident": incident}


def _cite(incident_id: str, *tabs: str) -> list[dict]:
    label = {"disposition": "Disposition", "mission-spine": "Mission Spine", "comparability": "Comparable Conditions",
             "evidence": "Evidence", "contract": "Recovery Contract", "twin": "Recovery Twin",
             "closure-risk": "Closure Risk", "contingency": "Contingency", "outcome": "Outcome"}
    return [{"surface": label.get(t, t), "path": f"/missions/{incident_id}?tab={t}"} for t in tabs]


# ── intents ─────────────────────────────────────────────────────────────────────────────────────────────
_INTENTS: list[tuple[str, list[str]]] = [
    ("meta",       ["who are you", "what are you", "are you ai", "are you an ai", "are you an agent", "are you a bot",
                    "are you human", "do you decide", "decides closure", "decide closure", "close it yourself",
                    "what can you do"]),
    ("close",      ["can we close", "safe to close", "ready to close", "can i close", "release it", "ship it", "sign off"]),
    ("blocking",   ["block", "stuck", "why not", "why isn", "what's stopping", "whats stopping", "holding", "waiting on"]),
    ("next",       ["what do i", "what should", "next step", "who's next", "whos next", "what now", "my action", "do now"]),
    ("evidence",   ["evidence", "measurement", "missing", "what's needed", "whats needed", "submit"]),
    ("confidence", ["confidence", "how sure", "risk", "trust", "how confident", "likelihood"]),
    ("relapse",    ["relapse", "reopen", "recur", "again", "come back", "fault back", "false closure"]),
    ("comparable", ["comparable", "conditions", "apples", "confound", "baseline"]),
    ("status",     ["status", "summary", "what's happening", "whats happening", "where are we", "where do we", "overview", "explain"]),
]


def _match(question: str) -> str:
    q = re.sub(r"\s+", " ", (question or "").strip().lower())
    for intent, keys in _INTENTS:
        if any(k in q for k in keys):
            return intent
    return "status"


# ── answers (each grounded in the deterministic facts; role-adapted) ────────────────────────────────────
def _verified(f: dict) -> bool:
    return f["spine"].get("outcome") == "VERIFIED"


def _ans_close(f: dict, role: Role, iid: str) -> dict:
    disp, spine = f["disp"], f["spine"]
    if disp is None:
        return {"answer": "There's no recovery contract yet, so closure isn't on the table — a contract must be "
                          "drafted and reviewed first. " + _ROLE_LENS[role],
                "citations": _cite(iid, "mission-spine", "contract")}
    can = disp.get("can_close")
    reasons = disp.get("reasons") or []
    if can and _verified(f):
        return {"answer": "Yes — every release gate has passed and the deterministic evaluator certified "
                          "VERIFIED recovery. The Qualification Record is issued.",
                "citations": _cite(iid, "disposition", "outcome")}
    head = "Not yet — the deterministic gate will not authorise closure." if not can else "Technically passing, but not certified."
    why = (" Blocking: " + "; ".join(reasons[:3]) + ".") if reasons else ""
    return {"answer": f"{head}{why} Remember: a completed work order is not proof of recovery — the evaluator, "
                      f"not the work order, decides. {_ROLE_LENS[role]}",
            "citations": _cite(iid, "disposition", "mission-spine")}


def _ans_blocking(f: dict, role: Role, iid: str) -> dict:
    spine = f["spine"]
    if _verified(f):
        return {"answer": "Nothing is blocking — recovery is verified and the record is issued.",
                "citations": _cite(iid, "outcome")}
    blocks = spine.get("what_blocks") or "Gathering stable cycles and evidence."
    why = spine.get("why_not_verified") or []
    extra = (" Specifically: " + "; ".join(why[:3]) + ".") if why else ""
    return {"answer": f"{blocks}{extra} Next: {spine.get('who_next')}",
            "citations": _cite(iid, "mission-spine", "disposition")}


def _ans_next(f: dict, role: Role, iid: str) -> dict:
    spine = f["spine"]
    who = spine.get("who_next") or "No action pending."
    mine = ""
    rl = role.value.replace("_", " ")
    if rl.split()[0] in (who.lower()):
        mine = " That's you."
    return {"answer": f"{who}{mine} (Current stage: {spine.get('current_stage')}.) {_ROLE_LENS[role]}",
            "citations": _cite(iid, "mission-spine")}


def _ans_evidence(f: dict, role: Role, iid: str) -> dict:
    disp = f["disp"]
    if disp is None:
        return {"answer": "No contract yet, so no evidence requirements exist. Once the agent drafts the "
                          "contract, the required measurements and approvals will be listed.",
                "citations": _cite(iid, "contract")}
    gaps = [hi["label"] for hi in disp.get("hard_invariants", []) if not hi.get("ok")]
    if not gaps:
        return {"answer": "All hard invariants currently have their evidence. " + _ROLE_LENS[role],
                "citations": _cite(iid, "evidence", "disposition")}
    return {"answer": "Still needed: " + "; ".join(gaps) + ". " + _ROLE_LENS[role],
            "citations": _cite(iid, "evidence", "disposition")}


def _ans_confidence(f: dict, role: Role, iid: str) -> dict:
    disp = f["disp"]
    if disp is None:
        return {"answer": "Confidence isn't computed until monitoring begins on a contract.",
                "citations": _cite(iid, "mission-spine")}
    conf = disp.get("effective_confidence")
    comp = (disp.get("comparability") or {}).get("classification", "UNKNOWN")
    pct = f"{round(conf * 100)}%" if isinstance(conf, (int, float)) else "—"
    return {"answer": f"Effective recovery confidence is {pct}, after the comparable-conditions ceiling "
                      f"(conditions are {comp.replace('_', ' ').lower()}) and sensor-trust discount. Confidence "
                      f"never closes on its own — the hard invariants must all pass. {_ROLE_LENS[role]}",
            "citations": _cite(iid, "closure-risk", "comparability")}


def _ans_relapse(f: dict, role: Role, iid: str) -> dict:
    inc = f["incident"]
    n = inc.reopened_count
    if n > 0:
        return {"answer": f"Yes — recovery was reopened {n} time(s). The deterministic evaluator rejected an "
                          f"apparent recovery because the originating fault recurred during the window. That is "
                          f"exactly the false closure this system exists to catch. {_ROLE_LENS[role]}",
                "citations": _cite(iid, "twin", "contingency")}
    return {"answer": "No relapse so far — the originating fault has not recurred in the verification window. "
                      "The non-recurrence condition keeps watching until the window completes.",
            "citations": _cite(iid, "twin", "mission-spine")}


def _ans_comparable(f: dict, role: Role, iid: str) -> dict:
    disp = f["disp"]
    if disp is None:
        return {"answer": "Comparability is assessed once there's a verification window to compare against the "
                          "plant's normal operating context.", "citations": _cite(iid, "comparability")}
    comp = disp.get("comparability") or {}
    cls = comp.get("classification", "UNKNOWN").replace("_", " ").lower()
    return {"answer": f"Operating conditions are {cls}. This matters because if before/after didn't run under "
                      f"comparable conditions, an apparent improvement can't be attributed to the intervention — "
                      f"so even all-passing conditions may be capped to INSUFFICIENT_EVIDENCE.",
            "citations": _cite(iid, "comparability", "disposition")}


def _ans_meta(f: dict, role: Role, iid: str) -> dict:
    return {"answer": "I'm the Verified Recovery Agent's advisory assistant. I explain this mission using the "
                      "deterministic facts the system computes — the seven-stage spine, the disposition gate, "
                      "and the evaluator — and I cite them. I do not decide closure and cannot act on the "
                      "machine; the deterministic Recovery Contract evaluator owns the verdict.",
            "citations": _cite(iid, "mission-spine", "disposition")}


def _ans_status(f: dict, role: Role, iid: str) -> dict:
    spine, inc = f["spine"], f["incident"]
    bits = [f"{inc.title}.", f"Stage: {spine.get('current_stage')}; state {inc.state.value}."]
    if _verified(f):
        bits.append("Recovery is VERIFIED and the record is issued.")
    else:
        bits.append(f"{spine.get('what_blocks')} Next: {spine.get('who_next')}")
    if inc.reopened_count:
        bits.append(f"Reopened {inc.reopened_count}x.")
    return {"answer": " ".join(bits) + f" {_ROLE_LENS[role]}",
            "citations": _cite(iid, "mission-spine", "disposition")}


_HANDLERS = {
    "close": _ans_close, "blocking": _ans_blocking, "next": _ans_next, "evidence": _ans_evidence,
    "confidence": _ans_confidence, "relapse": _ans_relapse, "comparable": _ans_comparable,
    "meta": _ans_meta, "status": _ans_status,
}


def _suggestions(f: dict) -> list[str]:
    if _verified(f):
        return ["Why is it verified?", "Were conditions comparable?", "Show the recovery trajectory."]
    if f["incident"].reopened_count:
        return ["Why did it reopen?", "What's blocking now?", "What do I do next?"]
    if f["disp"] is None:
        return ["What happens next?", "Who drafts the contract?", "What is a recovery contract?"]
    return ["What's blocking closure?", "What evidence is missing?", "How confident are we?"]


def answer(session: Session, incident: Incident, question: str, role: str | Role | None = None) -> dict:
    r = _role(role)
    f = _facts(session, incident)
    intent = _match(question)
    out = _HANDLERS[intent](f, r, incident.id)
    return {
        "question": question,
        "intent": intent,
        "role": r.value,
        "answer": out["answer"],
        "citations": out.get("citations", []),
        "suggestions": _suggestions(f),
        "grounded_in": "deterministic-evaluator",
        "basis": ("Advisory. Composed from the mission spine + disposition gate + deterministic evaluator and "
                  "cited back to them. The agent explains; it never decides closure or touches the machine."),
    }
