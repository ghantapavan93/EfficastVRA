"""Return-to-Service (Recovery) Certificate — the third primitive: the *proof* of recovery.

The trio: a Recovery **Contract** defines *what must become true*; the Expected Recovery **Signature**
reads *how it should become true*; this **Certificate** records *what actually happened and why closure
was accepted* — a single, exportable, human‑ and machine‑readable verification record.

It is purely **composed** (read‑only) from things the system already decided: the deterministic verdict,
the closure **provenance** (conditions, trust‑weighted evidence, human approvals, interventions,
proposed↔executed reconciliation, tamper‑evident audit chain) and the advisory intervention‑consistency
**signature**. It asserts nothing the deterministic evaluator didn't already own. Inspired by the
regulated world's return‑to‑service / maintenance‑release record, brought to general manufacturing.
"""

from __future__ import annotations

import hashlib

from sqlmodel import Session, select

from app.domain.base import utcnow
from app.domain.models import (
    AuditEvent,
    Incident,
    Machine,
    RecoveryContract,
    RecoveryWindow,
)
from app.services.provenance import closure_provenance
from app.services.recovery_signature import score_signature


def _audit_head_hash(session: Session, correlation_id: str) -> str:
    """The most recent audit entry's hash for this incident — the tamper‑evident chain head (the 'seal')."""
    row = session.exec(
        select(AuditEvent)
        .where(AuditEvent.correlation_id == correlation_id)
        .order_by(AuditEvent.seq.desc())  # type: ignore[attr-defined]
    ).first()
    return (row.entry_hash or "") if row else ""


def build_certificate(session: Session, incident: Incident) -> dict:
    """Assemble the Recovery Certificate (read‑only). ``status`` is certified | reopened | pending."""
    prov = closure_provenance(session, incident)
    if not prov.get("available"):
        return {"available": False, "incident_id": incident.id,
                "reason": prov.get("reason", "No recovery contract yet — nothing to certify.")}

    contract = session.get(RecoveryContract, incident.current_contract_id)
    machine = session.get(Machine, incident.machine_id)
    window = session.exec(
        select(RecoveryWindow).where(RecoveryWindow.contract_id == contract.id)
        .order_by(RecoveryWindow.sequence.desc())  # type: ignore[attr-defined]
    ).first()
    sig = score_signature(session, contract)

    # Comparable-Conditions ceiling (rule ccr-1.0): a certificate may not certify VERIFIED recovery when
    # operating conditions are not comparable, even if the hard gate closed the incident.
    from app.services.comparable_conditions import assess_comparability
    from app.services.recovery_policy import (
        ELIGIBLE,
        INSUFFICIENT,
        confounders_of,
        derive_effective_recovery_confidence,
    )

    closed = bool(prov["closed"])
    comp = assess_comparability(session, incident)
    policy = derive_effective_recovery_confidence(
        (sig.alignment + 1.0) / 2.0, comp.get("classification", "UNKNOWN"),
        comp.get("confidence_multiplier", 0.5), ELIGIBLE if closed else INSUFFICIENT,
        confounders=confounders_of(comp))
    certifiable = closed and policy.policy_result == "VERIFIED"
    if certifiable:
        status, verdict = "certified", "VERIFIED_RECOVERY"
    elif closed:  # hard gate closed it, but the comparability ceiling withholds certification
        status, verdict = "not_certified", "INSUFFICIENT_EVIDENCE"
    else:
        status = "reopened" if incident.reopened_count else "pending"
        verdict = prov["state"]
    head_hash = _audit_head_hash(session, incident.correlation_id)
    issued_at = (incident.closed_at or utcnow()).isoformat()

    # A deterministic certificate hash over the load‑bearing fields — same closure ⇒ same certificate.
    payload = "|".join([
        incident.id, contract.contract_no, str(contract.version), prov["state"],
        "verified" if closed else "open", head_hash,
        ",".join(f"{c['key']}:{c['status']}" for c in prov["conditions"]),
        ",".join(f"{a['decided_role']}:{a['decision']}" for a in prov["approvals"]),
    ])
    cert_hash = hashlib.sha256(payload.encode()).hexdigest()

    return {
        "available": True,
        "incident_id": incident.id,
        "certificate_id": f"RSC-{incident.id}-v{contract.version}",
        "status": status,
        "verdict": verdict,
        "issued_at": issued_at,
        "issuer": "Verified Recovery Agent — independent deterministic verification layer (advisory; "
                  "no machine control). Synthetic prototype.",
        # who/what it certifies
        "subject": {
            "incident_id": incident.id,
            "machine": (machine.name if machine else incident.machine_id),
            "machine_code": (machine.code if machine else None),
            "machine_model": (machine.machine_model if machine else None),
            "plant_id": incident.plant_id,
            "order_id": incident.order_id,
            "fault_code": incident.fault_code,
            "contract_no": contract.contract_no,
            "contract_version": contract.version,
        },
        # the evidence the verdict rests on (all from provenance)
        "conditions": prov["conditions"],
        "violated_conditions": prov["violated_conditions"],
        "evidence_summary": prov["evidence_summary"],
        "approvals": prov["approvals"],            # the human "signatures"
        "interventions": prov["interventions"],
        "reconciliation": prov["reconciliation"],
        "stable_cycles": (window.stable_streak if window else 0),
        "required_stable_cycles": (window.required_stable_cycles if window else 0),
        "reopened_count": incident.reopened_count,
        # intervention‑consistency (advisory) + comparable-conditions ceiling provenance (rule ccr-1.0)
        "signature": {"rung": sig.rung, "alignment": sig.alignment, "conditions_matched": sig.conditions_matched},
        "comparability": {"classification": comp.get("classification", "UNKNOWN"),
                          "confidence_multiplier": comp.get("confidence_multiplier"),
                          "confounding_dimensions": policy.confounding_dimensions},
        "policy_provenance": policy.as_provenance(),
        # tamper‑evident seal
        "audit": {"intact": bool(prov["audit"].get("ok")), "entries": prov["audit"].get("count"),
                  "head_hash": head_hash},
        "certificate_hash": cert_hash,
        "trustworthy": bool(prov["trustworthy"]),
        "summary": prov["summary"],
        "basis": ("Composed read‑only from the deterministic verdict, the gateway's proposal/execution log, "
                  "and the tamper‑evident audit chain — not from the LLM. A certificate records a verified "
                  "recovery; it never causes one. Synthetic PROTOTYPE_ASSUMPTION data."),
    }
