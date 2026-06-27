"""False-Closure Risk Score (FCRS) — the thesis as an actionable, explainable number.

Answers, *before* a human releases quality / closes: **how likely is it that closing now would be a
false closure** (an "apparently recovered" line that actually relapses)? It is a transparent, deterministic
composite of the signals the system already produces — the intervention‑consistency **signature**, the
**relapse precursor** (forecaster), the **stable‑cycle** margin, and the **weakest validated evidence** —
each surfaced with its own contribution so the score is auditable, not a black box. A recurring fault in
the window is a hard override to high risk.

Read‑only and **advisory**: it never closes, reopens, or gates anything — the deterministic evaluator owns
closure. It is a decision aid for the human at the approval step. Its own skill is measurable via the
calibration harness (`services/calibration.py` / `/api/calibration`).
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.domain.models import (
    EvidenceItem,
    EvidenceRequirement,
    Incident,
    RecoveryContract,
    RecoveryObservation,
    RecoveryWindow,
)
from app.services.evidence_quality import classify
from app.services.quality import quality_release_satisfied
from app.services.recovery_signature import score_signature

# Factor weights (PROTOTYPE_ASSUMPTIONs; the discriminating relapse signals dominate). Renormalized over
# whatever factors are computable for the incident's current state.
_W = {
    "signature": 0.45,    # intervention inconsistency (1 − signature p_holds)
    "precursor": 0.30,    # live relapse precursor (forecaster p_relapse)
    "streak": 0.15,       # stable‑cycle shortfall vs the contract's required window
    "evidence": 0.10,     # weakest *validated* evidence (1 − min trust)
}
_LOW, _HIGH = 0.25, 0.60   # band thresholds


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _latest_window(session: Session, contract_id: str) -> RecoveryWindow | None:
    return session.exec(
        select(RecoveryWindow).where(RecoveryWindow.contract_id == contract_id)
        .order_by(RecoveryWindow.sequence.desc())  # type: ignore[attr-defined]
    ).first()


def assess_false_closure_risk(session: Session, incident: Incident) -> dict:
    contract = (session.get(RecoveryContract, incident.current_contract_id)
                if incident.current_contract_id else None)
    if contract is None:
        return {"available": False, "incident_id": incident.id,
                "reason": "No recovery contract yet — closure risk is available once one is drafted."}

    factors: list[dict] = []

    # 1. intervention inconsistency (signature) — the dominant signal
    sig = score_signature(session, contract)
    p_holds = (sig.alignment + 1.0) / 2.0
    factors.append({"key": "signature", "label": "Intervention inconsistency",
                    "weight": _W["signature"], "value": _clamp(1.0 - p_holds),
                    "detail": f"signature alignment {sig.alignment:+.2f} ({sig.rung.replace('_', ' ')})"})

    # 2. live relapse precursor (forecaster) — only when a live forecast exists
    try:
        from app.services.forecaster import forecast as _forecast
        fc = _forecast(session, contract)
        if getattr(fc, "available", False) and getattr(fc, "p_relapse", None) is not None:
            factors.append({"key": "precursor", "label": "Relapse precursor", "weight": _W["precursor"],
                            "value": _clamp(float(fc.p_relapse)),
                            "detail": f"forecaster p(relapse) {float(fc.p_relapse):.2f}"})
    except Exception:  # advisory — never let a forecaster hiccup break the risk read
        pass

    # 3. stable‑cycle shortfall
    win = _latest_window(session, contract.id)
    fault_in_window = False
    if win is not None:
        required = win.required_stable_cycles or 30
        shortfall = _clamp((required - win.stable_streak) / required) if required else 0.0
        factors.append({"key": "streak", "label": "Stable‑cycle shortfall", "weight": _W["streak"],
                        "value": shortfall, "detail": f"{win.stable_streak}/{required} stable cycles"})
        obs = session.exec(
            select(RecoveryObservation).where(RecoveryObservation.window_id == win.id)
        ).all()
        fault_in_window = any(o.fault_code for o in obs)

    # 4. weakest validated evidence
    reqs = {r.id: r for r in session.exec(
        select(EvidenceRequirement).where(EvidenceRequirement.incident_id == incident.id)).all()}
    items = session.exec(
        select(EvidenceItem).where(EvidenceItem.incident_id == incident.id)).all()
    contributing = [classify(i, reqs.get(i.requirement_id))["trust"] for i in items if i.valid]
    if contributing:
        min_trust = min(contributing)
        factors.append({"key": "evidence", "label": "Weakest validated evidence", "weight": _W["evidence"],
                        "value": _clamp(1.0 - min_trust), "detail": f"min trust {min_trust:.2f}"})

    # composite (renormalized over available factors) + per‑factor contribution
    den = sum(f["weight"] for f in factors) or 1.0
    for f in factors:
        f["contribution"] = round(f["weight"] / den * f["value"], 3)
    risk = sum(f["contribution"] for f in factors)

    # hard override: the originating fault recurred in the window → a closure now is a false closure
    if fault_in_window:
        risk = max(risk, 0.9)

    risk = round(_clamp(risk), 3)
    band = "high" if risk >= _HIGH else ("elevated" if risk >= _LOW else "low")
    quality_ok, _ = quality_release_satisfied(session, contract.id)
    dominant = max(factors, key=lambda f: f["contribution"]) if factors else None

    recommendation = {
        "low": "Relapse risk is low — closure is well‑supported by the signals.",
        "elevated": "Elevated relapse risk — extend monitoring or strengthen the dominant factor before closing.",
        "high": "High relapse risk — do not close; a closure now would likely be a false closure.",
    }[band]
    if fault_in_window:
        recommendation = "The originating fault recurred during the window — do not close (the evaluator reopens)."

    return {
        "available": True,
        "incident_id": incident.id,
        "risk": risk,
        "risk_pct": round(risk * 100),
        "band": band,
        "recommendation": recommendation,
        "dominant_driver": (dominant["label"] if dominant else None),
        "fault_in_window": fault_in_window,
        "quality_released": bool(quality_ok),
        "factors": factors,
        "basis": ("Advisory, read‑only decision aid — NOT the closure verdict (the deterministic evaluator "
                  "owns closure). A transparent weighted blend of the intervention‑consistency signature, "
                  "the relapse precursor, the stable‑cycle margin, and the weakest validated evidence; a "
                  "recurring fault forces high. Each factor's contribution is shown. The score's own skill "
                  "is measured by the calibration harness (/api/calibration). Synthetic PROTOTYPE_ASSUMPTION."),
    }
