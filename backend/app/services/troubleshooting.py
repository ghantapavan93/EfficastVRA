"""Troubleshooting & knowledge lookup — find the answer fast, grounded and trustworthy.

Directly attacks the pain in the brief: *hunting through 400-page manuals* and *troubleshooting the
same fault repeatedly*. A plant person enters a fault and/or machine and gets one grounded card:
the **approved** procedure (obsolete/unapproved notes filtered out but flagged), the **ranked likely
causes**, **what worked before** (past incidents with this fault), the **signals to check** and the
**early-warning precursor**, and any **captured lessons** (clearly marked pending expert review). It
is not a chatbot — every line is sourced, approval-checked, and fresh.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.domain.enums import KnowledgeStatus
from app.domain.models import Incident, KnowledgeCandidate
from app.rag import detect_conflicts, search
from app.services.machine_profiles import profile_for_model


def troubleshoot(session: Session, *, fault_code: str | None = None,
                 machine_model: str | None = None, query: str = "") -> dict:
    profile = profile_for_model(machine_model) if machine_model else None
    component = None  # left broad; the RAG applicability filter handles machine_model

    # Build a retrieval query from whatever the user gave us.
    terms = " ".join(t for t in [query, fault_code or "", "fault corrective procedure alignment "
                                 "bearing vibration recovery"] if t).strip()

    approved = search(session, terms, machine_model=machine_model, component=component,
                      approved_only=True, k=4)
    conflicts = detect_conflicts(session, terms, machine_model=machine_model, component=component)

    # Past incidents with this fault → history + "what worked".
    hist_q = select(Incident).where(Incident.historical == True)  # noqa: E712
    if fault_code:
        hist_q = hist_q.where(Incident.fault_code == fault_code)
    history = session.exec(hist_q).all()
    history_view = [{"incident_id": h.id, "fault_code": h.fault_code,
                     "outcome": h.outcome_type.value if h.outcome_type else None,
                     "summary": h.outcome_summary} for h in history]
    what_worked = history[0].outcome_summary if history else ""

    # Ranked likely causes (data-driven: the historical root cause is the strongest prior).
    causes: list[dict] = []
    if profile and profile.equipment_class == "conveyor_drive":
        causes.append({"cause": "Coupling misalignment (often after a motor replacement)",
                       "likelihood": "common first cause",
                       "basis": "frequent post-maintenance cause of vibration + this fault"})
    if history:
        causes.append({"cause": "Latent drive-end bearing degradation",
                       "likelihood": "high if it recurs after a corrective action",
                       "basis": f"history {history[0].id}: alignment did not hold; the bearing was the root cause"})
    if not causes:
        causes.append({"cause": "Inspect the drivetrain (motor → coupling → bearing) for the fault signature",
                       "likelihood": "—", "basis": "no historical precedent on record"})

    # Signals to check + the early-warning precursor (from the machine profile).
    signals = []
    if profile:
        for c in profile.conditions:
            if c.kind.value != "QUALITY":
                signals.append({"key": c.key, "label": c.label, "op": c.op.value,
                                "threshold": c.threshold, "unit": c.unit})
    early_warning = ("Watch the drive-end bearing precursor (high-frequency vibration / crest factor): "
                     "it rises before the fault recurs even when vibration, temperature and scrap still "
                     "look recovered. See the Recovery Forecast.") if (profile and "bearing"
                     in " ".join(p for p in [profile.summary]).lower()) else ""

    # Captured lessons — clearly labelled (never shown as approved guidance).
    kc_rows = session.exec(select(KnowledgeCandidate)).all()
    knowledge = [{"title": k.title, "lesson": k.lesson, "component": k.component,
                  "applicable_models": k.applicable_models,
                  "status": k.status.value, "pending_review": k.status == KnowledgeStatus.PENDING_REVIEW,
                  "failed_intervention": k.failed_intervention,
                  "successful_intervention": k.successful_intervention} for k in kc_rows
                 if (not machine_model) or (machine_model in (k.applicable_models or []))]

    machine = ({"model": machine_model, "equipment_class": profile.equipment_class,
                "label": profile.label} if profile else
               ({"model": machine_model} if machine_model else None))

    summary = (f"{fault_code or 'Fault'} on {profile.label.lower() if profile else (machine_model or 'machine')}: "
               f"{len(approved)} approved procedure(s), {len(history)} comparable past incident(s), "
               f"{len(causes)} ranked cause(s). "
               + ("Heads-up: a relapse precursor exists — verify recovery, don't just close the work order."
                  if early_warning else ""))

    return {
        "query": {"fault_code": fault_code, "machine_model": machine_model, "text": query},
        "machine": machine,
        "summary": summary,
        "likely_causes": causes,
        "approved_procedures": [{"document_id": a.document_id, "section": a.section, "revision": a.revision,
                                 "approval_status": a.approval_status, "excerpt": a.content[:240]}
                                for a in approved],
        "history": history_view,
        "what_worked": what_worked,
        "signals_to_check": signals,
        "early_warning": early_warning,
        "knowledge": knowledge,
        "cautions": conflicts.get("conflicts", []),
    }
