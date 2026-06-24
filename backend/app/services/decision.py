"""Decision Intelligence — the risk-adjusted, dollar-quantified, senior-manager view.

Cross-industry research (docs/CROSS_INDUSTRY_RESEARCH.md) found the gap manufacturing AI agents lag on:
finance agents have **risk-adjusted decision frameworks**; manufacturing agents are technically
focused (detect → diagnose → verify) and rarely speak the language a plant manager actually decides
in — **money and risk**. This layer adds two cross-industry primitives:

  1. Decision economics (finance) — production & cost exposure, and the **expected cost** of each option
     (close now / keep monitoring / pre-stage the contingency), risk-weighted by the Forecaster's
     P(relapse). It recommends the lowest-expected-cost action, with the numbers.
  2. FMEA (aviation/reliability engineering) — failure modes scored Severity × Occurrence × Detection =
     **RPN**, ranked; it also shows how the agent's own Forecaster *lowers* RPN by improving detection.

Advisory only. The deterministic evaluator still decides closure; this informs the human's call.
Cost/severity figures are PROTOTYPE_ASSUMPTIONs (configurable), not Efficast data.
"""

from __future__ import annotations

import os

from sqlmodel import Session

from app.domain.models import Incident, Machine, ProductionOrder
from app.services.forecaster import forecast

# Illustrative cost model (override via env). PROTOTYPE_ASSUMPTION — not real Efficast figures.
DOWNTIME_COST_PER_HOUR = float(os.getenv("VRA_DOWNTIME_COST_PER_HOUR", "1800"))
SCRAP_COST_PER_UNIT = float(os.getenv("VRA_SCRAP_COST_PER_UNIT", "12"))
CONTINGENCY_PREP_COST = float(os.getenv("VRA_CONTINGENCY_PREP_COST", "300"))  # reserve part + standby tech

# Reliability assumptions for a false closure (fault recurs after a premature close).
_RELAPSE_DOWNTIME_H = 2.5          # re-diagnose + the real fix
_RELAPSE_SCRAP_UNITS = 80          # scrap before the recurrence is caught (false closure — nobody watching)
_PRESTAGED_DOWNTIME_H = 1.0        # part on hand + tech on standby → faster recovery
_PRESTAGED_SCRAP_UNITS = 30
_MONITORED_SCRAP_UNITS = 30        # scrap that still accrues during the relapse cycle before monitoring catches it


def _usd(x: float) -> int:
    return int(round(x))


def decide(session: Session, incident: Incident) -> dict:
    machine = session.get(Machine, incident.machine_id)
    order = session.get(ProductionOrder, incident.order_id) if incident.order_id else None

    # P(relapse): from the live Forecaster when monitoring; else uncertain.
    p_relapse = 0.5
    forecast_state = "unavailable"
    if incident.current_contract_id:
        from app.domain.models import RecoveryContract

        contract = session.get(RecoveryContract, incident.current_contract_id)
        if contract is not None:
            f = forecast(session, contract)
            if f.available:
                p_relapse = f.p_relapse
                forecast_state = "live"

    # ── 1. production & cost exposure ──
    cycle_s = float((machine.baseline or {}).get("cycle_time_s", 12.2)) if machine else 12.2
    throughput_h = round(3600.0 / cycle_s, 1) if cycle_s else 0.0
    units_remaining = order.qty_remaining if order else 0
    hours_to_complete = round(units_remaining / throughput_h, 1) if throughput_h else 0.0
    false_closure_cost = _RELAPSE_DOWNTIME_H * DOWNTIME_COST_PER_HOUR + _RELAPSE_SCRAP_UNITS * SCRAP_COST_PER_UNIT

    impact = {
        "order_id": order.id if order else None,
        "units_remaining": units_remaining,
        "throughput_per_hour": throughput_h,
        "hours_to_complete": hours_to_complete,
        "false_closure_exposure_usd": _usd(false_closure_cost),
        "assumptions": {"downtime_cost_per_hour": DOWNTIME_COST_PER_HOUR,
                        "scrap_cost_per_unit": SCRAP_COST_PER_UNIT,
                        "contingency_prep_cost": CONTINGENCY_PREP_COST},
    }

    # ── 2. risk-adjusted options (expected cost) ──
    close_now = p_relapse * false_closure_cost
    # Monitoring catches the relapse at recurrence (no quality escape), but scrap still accrues until
    # detection — so it carries a scrap term too, consistent with the close-now model (fixes the bias
    # where dropping scrap made monitoring look artificially cheap).
    keep_monitoring = p_relapse * (_RELAPSE_DOWNTIME_H * DOWNTIME_COST_PER_HOUR
                                   + _MONITORED_SCRAP_UNITS * SCRAP_COST_PER_UNIT)
    pre_stage = CONTINGENCY_PREP_COST + p_relapse * (_PRESTAGED_DOWNTIME_H * DOWNTIME_COST_PER_HOUR
                                                     + _PRESTAGED_SCRAP_UNITS * SCRAP_COST_PER_UNIT)
    options = [
        {"action": "close_now", "label": "Close the incident now",
         "expected_cost_usd": _usd(close_now),
         "rationale": "Fastest, but you carry the full false-closure cost if the fault recurs."},
        {"action": "keep_monitoring", "label": "Keep monitoring to full window",
         "expected_cost_usd": _usd(keep_monitoring),
         "rationale": "Catches a relapse before bad product ships (no quality escape); some scrap still accrues until detection; delays closure."},
        {"action": "pre_stage_contingency", "label": "Pre-stage the bearing contingency",
         "expected_cost_usd": _usd(pre_stage),
         "rationale": "Reserve the part + ready a technician now, so a relapse is recovered fast."},
    ]
    best = min(options, key=lambda o: o["expected_cost_usd"])
    best["recommended"] = True
    recommendation = {
        "action": best["action"], "label": best["label"],
        "headline": f"Recommended: {best['label'].lower()} (expected cost ${best['expected_cost_usd']:,}).",
        "why": (f"At {round(p_relapse * 100)}% relapse probability, '{best['label'].lower()}' has the lowest "
                f"risk-adjusted cost. Closing now risks ${_usd(close_now):,} on average."),
    }

    # ── 3. FMEA (S × O × D = RPN), detection improved by the Forecaster ──
    fmea = [
        {"failure_mode": "Drive-end bearing degradation", "effect": "F27 recurrence · unplanned downtime",
         "severity": 8, "occurrence": 6, "detection": 3, "detection_without_agent": 7},
        {"failure_mode": "Coupling misalignment", "effect": "Vibration rise · short stops · scrap",
         "severity": 6, "occurrence": 5, "detection": 4, "detection_without_agent": 6},
        {"failure_mode": "Premature work-order closure", "effect": "False recovery ships · rework",
         "severity": 9, "occurrence": 4, "detection": 2, "detection_without_agent": 8},
    ]
    for m in fmea:
        m["rpn"] = m["severity"] * m["occurrence"] * m["detection"]
        m["rpn_without_agent"] = m["severity"] * m["occurrence"] * m["detection_without_agent"]
    fmea.sort(key=lambda m: m["rpn"], reverse=True)

    # When there is no live forecast (incident closed/reopened/pre-monitoring), p_relapse is a neutral
    # 0.5 default — say so, so the dollar figures aren't read as a calibrated live estimate.
    indicative = forecast_state != "live"
    caveat = (" — INDICATIVE: no live forecast for this incident state, p_relapse is a neutral default"
              if indicative else "")
    summary = (f"At {round(p_relapse * 100)}% relapse risk ({forecast_state}{caveat}), false-closure "
               f"exposure is ~${_usd(false_closure_cost):,}. {recommendation['label']} minimises expected "
               "cost. The agent's forecaster cuts detection RPN materially (see FMEA).")
    if indicative:
        recommendation["headline"] = "Indicative only (no live forecast): " + recommendation["headline"]

    return {
        "available": True, "incident_id": incident.id, "p_relapse": p_relapse,
        "forecast_state": forecast_state, "indicative": indicative, "impact": impact, "options": options,
        "recommendation": recommendation, "fmea": fmea,
        "fmea_note": ("Detection (D) improved by the Recovery Forecaster's precursor monitoring — lower D "
                      "means lower RPN; the 'without agent' column shows the risk you'd carry blind. "
                      "S/O/D scores here are illustrative PROTOTYPE_ASSUMPTIONs (not measured), so the "
                      "agent-vs-blind delta is indicative, not an empirical benchmark."),
        "summary": summary,
        "advisory": "Advisory only — the deterministic evaluator decides closure; this informs the human's call.",
    }
