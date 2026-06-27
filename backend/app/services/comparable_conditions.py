"""Comparable-Conditions Gate — did before/after run under conditions we can responsibly compare?

Observing improvement after an intervention does NOT prove the intervention caused it. If the verification
window ran under *easier* conditions — a different product/recipe, lower speed or load, a fresh-but-different
material lot, a degraded or uncalibrated sensor — the apparent recovery is a **confound**, not the repair.

This deterministic gate compares the plant's normal operating context (the reference) against the context
observed during the verification window, dimension by dimension, and returns one of:

    COMPARABLE · PARTIALLY_COMPARABLE · NOT_COMPARABLE · UNKNOWN

with a per-dimension breakdown and a confidence multiplier. It is the causal-honesty backbone: it turns
"we observed improvement" into "we observed improvement *under comparable conditions*."

Read-only & advisory — it never changes the verdict (the deterministic evaluator owns closure). It *informs*
the Recovery Disposition (NOT_COMPARABLE can drive INSUFFICIENT_EVIDENCE) and the causal-confidence read.
Method lineage: matched/comparable operating windows + interrupted-time-series confound control, reduced to
a deterministic MVP. Synthetic PROTOTYPE_ASSUMPTION data.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from app.domain.models import Incident, RecoveryContract, RecoveryWindow

# Each dimension is weighted: 'key' shifts break comparability; 'minor' shifts weaken it; 'info' shifts are
# normal operational variation (a new lot / a shift change) and are reported but never penalised.
_DIMS = [
    {"key": "product", "type": "cat", "weight": "key", "label": "Product / recipe"},
    {"key": "machine_mode", "type": "cat", "weight": "key", "label": "Machine mode"},
    {"key": "load", "type": "cat", "weight": "key", "label": "Load"},
    {"key": "sensor_health", "type": "cat", "weight": "key", "label": "Sensor health"},
    {"key": "speed_pct", "type": "num", "tol_rel": 0.10, "weight": "key", "label": "Line speed"},
    {"key": "ambient_c", "type": "num", "tol_abs": 6.0, "weight": "minor", "label": "Ambient temperature"},
    {"key": "material_lot", "type": "cat", "weight": "info", "label": "Material lot"},
    {"key": "shift", "type": "cat", "weight": "info", "label": "Shift"},
]
_MULT = {"COMPARABLE": 1.0, "PARTIALLY_COMPARABLE": 0.6, "NOT_COMPARABLE": 0.2, "UNKNOWN": 0.5}
_IMPLICATION = {
    "COMPARABLE": "Before and after ran under comparable conditions — improvement can be attributed to the "
                  "intervention with normal confidence.",
    "PARTIALLY_COMPARABLE": "Minor operating-condition shifts (or incomplete context) — attribution is "
                            "weaker; treat the causal read as reduced confidence.",
    "NOT_COMPARABLE": "Operating conditions changed materially — the apparent recovery may be a confound, "
                      "not the repair. Do not certify verified recovery on this evidence alone.",
    "UNKNOWN": "Operating context was not captured — comparability cannot be established.",
}


def _latest_window(session: Session, contract_id: str) -> Optional[RecoveryWindow]:
    return session.exec(
        select(RecoveryWindow).where(RecoveryWindow.contract_id == contract_id)
        .order_by(RecoveryWindow.sequence.desc())  # type: ignore[attr-defined]
    ).first()


def classify_context(baseline: dict, observed: dict) -> dict:
    """Pure classifier: compare two operating-context dicts → classification + per-dimension breakdown."""
    dims: list[dict] = []
    key_shifts = minor_shifts = unknown_rel = 0
    for spec in _DIMS:
        b = baseline.get(spec["key"])
        o = observed.get(spec["key"])
        if b is None or o is None:
            status = "unknown"
        elif spec["type"] == "num":
            try:
                if "tol_rel" in spec:
                    status = "shift" if abs(float(o) - float(b)) / max(abs(float(b)), 1e-9) > spec["tol_rel"] else "match"
                else:
                    status = "shift" if abs(float(o) - float(b)) > spec["tol_abs"] else "match"
            except (TypeError, ValueError):
                status = "unknown"
        else:  # categorical
            status = "match" if b == o else "shift"

        weight = spec["weight"]
        if weight in ("key", "minor"):
            if status == "shift":
                if weight == "key":
                    key_shifts += 1
                else:
                    minor_shifts += 1
            elif status == "unknown":
                unknown_rel += 1
        note = ("confound — breaks comparability" if (status == "shift" and weight == "key")
                else "weakens comparability" if (status == "shift" and weight == "minor")
                else "normal variation" if weight == "info"
                else "")
        dims.append({"key": spec["key"], "label": spec["label"], "baseline": b, "observed": o,
                     "status": status, "weight": weight, "note": note})

    known_relevant = [d for d in dims if d["weight"] in ("key", "minor") and d["status"] != "unknown"]
    if not known_relevant:
        classification = "UNKNOWN"
    elif key_shifts >= 1:
        classification = "NOT_COMPARABLE"
    elif minor_shifts >= 1 or unknown_rel > 0:
        classification = "PARTIALLY_COMPARABLE"
    else:
        classification = "COMPARABLE"

    return {
        "classification": classification,
        "confidence_multiplier": _MULT[classification],
        "key_shifts": key_shifts,
        "minor_shifts": minor_shifts,
        "dimensions": dims,
    }


def assess_comparability(session: Session, incident: Incident) -> dict:
    contract = (session.get(RecoveryContract, incident.current_contract_id)
                if incident.current_contract_id else None)
    if contract is None:
        return {"available": False, "incident_id": incident.id,
                "reason": "No recovery contract yet — comparability is available once monitoring begins."}

    win = _latest_window(session, contract.id)
    if win is None:
        return {"available": True, "incident_id": incident.id, "classification": "UNKNOWN",
                "confidence_multiplier": _MULT["UNKNOWN"], "key_shifts": 0, "minor_shifts": 0,
                "dimensions": [], "implication": _IMPLICATION["UNKNOWN"],
                "reason": "No verification window yet.", "basis": _BASIS}

    res = classify_context(win.baseline_context or {}, win.observed_context or {})
    res.update({
        "available": True,
        "incident_id": incident.id,
        "implication": _IMPLICATION[res["classification"]],
        "basis": _BASIS,
    })
    return res


_BASIS = ("Advisory & read-only — never changes the verdict (the deterministic evaluator owns closure). "
          "Compares the plant's normal operating context against the verification window's context; a "
          "material shift on a key dimension means the apparent recovery may be a confound. Synthetic "
          "PROTOTYPE_ASSUMPTION data; in production this context comes from the MES.")
