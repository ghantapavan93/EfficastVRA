"""MAIA outbound message contract.

Structured, bounded messages for the WhatsApp/MAIA surface. WhatsApp is a **communication surface only**:
a message carries a title, a short body, a severity, and a small set of **deep-links into the app** — never
free-form text that executes tools and never an evidence-review workflow. Tool execution stays behind the
Agent Action Gateway in the app; messaging just points a human at the right screen.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MaiaSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class MaiaAction(BaseModel):
    """A bounded action = a deep-link into the app. There is deliberately no 'tool'/'command' field —
    messaging can never execute a tool."""
    label: str
    deep_link: str


class MaiaMessage(BaseModel):
    kind: str
    incident_id: str
    title: str
    body: str
    severity: MaiaSeverity = MaiaSeverity.INFO
    actions: list[MaiaAction] = Field(default_factory=list)
    surface: str = "whatsapp"   # a communication surface only


MAIA_KINDS = [
    "verification_started", "evidence_missing", "comparability_failed", "recovery_failed",
    "incident_reopening_proposed", "conditional_operation_proposed", "recovery_verified",
]

_S = MaiaSeverity
_SPEC: dict[str, tuple[MaiaSeverity, str, str, list[tuple[str, str]]]] = {
    "verification_started": (_S.INFO, "Verification started — {id}",
        "Recovery is now being verified over the contract window. No action needed yet.",
        [("View mission", "/missions/{id}")]),
    "evidence_missing": (_S.WARNING, "Evidence needed — {id}",
        "Required evidence is missing or stale; closure is blocked until it is provided.",
        [("Provide evidence", "/missions/{id}?tab=evidence")]),
    "comparability_failed": (_S.WARNING, "Conditions not comparable — {id}",
        "Operating conditions were not comparable, so recovery can't be attributed to the intervention.",
        [("View comparable conditions", "/missions/{id}?tab=comparability")]),
    "recovery_failed": (_S.CRITICAL, "Recovery failed — {id}",
        "A recovery condition was violated. The incident did not close.",
        [("View outcome", "/missions/{id}?tab=outcome")]),
    "incident_reopening_proposed": (_S.WARNING, "Reopening proposed — {id}",
        "A relapse was detected; reopening and a contingency are proposed for your approval.",
        [("Review contingency", "/missions/{id}?tab=contingency")]),
    "conditional_operation_proposed": (_S.WARNING, "Conditional operation proposed — {id}",
        "Production may continue under temporary restrictions while a condition is deferred — needs approval.",
        [("Review waiver", "/missions/{id}?tab=recovery-debt")]),
    "recovery_verified": (_S.INFO, "Recovery verified — {id}",
        "All conditions passed under comparable conditions and quality was released; the incident is closed.",
        [("View certificate", "/missions/{id}?tab=certificate")]),
}


def build_maia_message(kind: str, incident_id: str) -> MaiaMessage:
    if kind not in _SPEC:
        raise ValueError(f"unknown MAIA message kind: {kind}")
    sev, title, body, actions = _SPEC[kind]
    return MaiaMessage(
        kind=kind, incident_id=incident_id, title=title.format(id=incident_id), body=body, severity=sev,
        actions=[MaiaAction(label=lbl, deep_link=link.format(id=incident_id)) for lbl, link in actions],
    )


def maia_messages_for(session, incident) -> list[MaiaMessage]:
    """Derive the applicable structured message(s) from the incident's current disposition. Read-only."""
    from app.services.disposition import assess_disposition

    d = assess_disposition(session, incident)
    if not d.get("available"):
        return [build_maia_message("verification_started", incident.id)]
    disp = d.get("disposition")
    comparable = (d.get("comparability") or {}).get("classification")
    kind = {
        "VERIFIED": "recovery_verified",
        "FAILED": "recovery_failed",
        "CONDITIONAL": "conditional_operation_proposed",
        "ESCALATION_REQUIRED": "incident_reopening_proposed",
        "IN_PROGRESS": "verification_started",
    }.get(disp)
    if kind is None:  # INSUFFICIENT_EVIDENCE → distinguish a comparability confound from a missing gate
        kind = "comparability_failed" if comparable in ("NOT_COMPARABLE", "UNKNOWN") else "evidence_missing"
    return [build_maia_message(kind, incident.id)]
