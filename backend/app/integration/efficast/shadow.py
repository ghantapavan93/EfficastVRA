"""Shadow mode — evaluate real/replayed events and compare to the plant's actual outcome, writing NOTHING.

Shadow mode is the honest way to earn trust before acting: consume an enveloped event stream, reconcile it,
run the SAME deterministic cores the live system uses (``score_observations`` for the recovery signature,
``classify_context`` for comparable conditions), propose a disposition, and compare it against the outcome
the bundle says the plant actually reached. It performs **no external writes** — it takes no DB session and
calls no gateway/port write methods, so the no-write guarantee is structural, not merely promised.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional, Union

from app.domain.models import RecoveryObservation
from app.integration.efficast.contract import (
    EfficastEvent,
    MachineEvent,
    ProductionOrderContext,
    RecoveryDecisionPublication,
    SensorHealth,
    TelemetryObservation,
)
from app.integration.efficast.reconciliation import ReconciliationResult, reconcile
from app.services.calibration import _conveyor_conditions
from app.services.comparable_conditions import classify_context
from app.services.recovery_signature import score_observations

_METRIC_FIELD = {
    "vibration_rms": "vibration", "temperature": "temperature", "cycle_time": "cycle_time",
    "scrap_pct": "scrap_pct", "bearing_precursor": "bearing_precursor",
}
_REQUIRED_STABLE = 30
_NORMAL_CONTEXT = {"product": "PKG-STD-12", "speed_pct": 95.0, "load": "nominal", "material_lot": "LOT-7741",
                   "machine_mode": "AUTO", "shift": "A", "ambient_c": 24.0, "sensor_health": "ok"}


@dataclass
class ShadowIncidentReport:
    correlation_id: str
    proposed_disposition: str
    actual_outcome: Optional[str]
    agreement: Optional[bool]
    signature_rung: str
    alignment: float
    comparability: str
    sensor_trust: str
    observed_cycles: int
    reasons: list[str] = field(default_factory=list)


@dataclass
class ShadowReport:
    incidents: list[ShadowIncidentReport]
    reconciliation: ReconciliationResult
    writes_performed: int = 0   # always 0 — shadow mode never writes (no session, no port writes)

    @property
    def agreement_rate(self) -> Optional[float]:
        judged = [i for i in self.incidents if i.agreement is not None]
        return round(sum(1 for i in judged if i.agreement) / len(judged), 3) if judged else None


def _observations_from(events: list[EfficastEvent]) -> list[RecoveryObservation]:
    """Fold per-metric telemetry (grouped by source_timestamp) + F27 machine events → cycle observations."""
    fault_ts = {e.source_timestamp for e in events if isinstance(e, MachineEvent) and e.event_code == "F27"}
    by_ts: "OrderedDict[object, dict]" = OrderedDict()
    for e in sorted([e for e in events if isinstance(e, TelemetryObservation)], key=lambda x: x.source_timestamp):
        by_ts.setdefault(e.source_timestamp, {})[e.metric] = e.value
    obs: list[RecoveryObservation] = []
    for i, (ts, metrics) in enumerate(by_ts.items(), start=1):
        obs.append(RecoveryObservation(
            tenant_id="shadow", incident_id="shadow", contract_id="shadow", window_id="shadow", at=ts,
            cycle_index=i, fault_code=("F27" if ts in fault_ts else None),
            **{field_: metrics.get(metric) for metric, field_ in _METRIC_FIELD.items()},
        ))
    return obs


def _sensor_trust(events: list[EfficastEvent]) -> str:
    """Worse of the declared SensorHealth status and the Sensor Trust Gate's DERIVED classification over the
    vibration telemetry series (range / flatline / noise / calibration)."""
    from app.services.sensor_trust import classify_sensor

    order = {"untrusted": 0, "unknown": 1, "degraded": 2, "trusted": 3}
    declared = [e.status for e in events if isinstance(e, SensorHealth)]
    decl = min(declared, key=lambda s: order.get(s, 1)) if declared else "unknown"
    vib = [e.value for e in events if isinstance(e, TelemetryObservation) and e.metric == "vibration_rms"]
    derived = classify_sensor(vib, metric="vibration").status.lower()
    return min([decl, derived], key=lambda s: order.get(s, 1))


def _propose(sig, comparability: str, trust: str, observations: list[RecoveryObservation]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if any(o.fault_code for o in observations):
        return "failed", ["A monitored fault recurred during the window."]
    if trust in ("untrusted", "unknown"):
        return "insufficient_evidence", [f"Sensor trust is {trust} — a measurement we can't trust can't satisfy a hard condition."]
    if comparability in ("NOT_COMPARABLE", "UNKNOWN"):
        return "insufficient_evidence", [f"Operating conditions {comparability.lower()} — recovery can't be attributed."]
    if sig.rung in ("strongly_consistent", "consistent_with_intervention"):
        return "verified", ["Signature consistent with the intervention; stable + comparable + trusted."]
    if sig.rung == "recovery_observed":
        return "insufficient_evidence", ["Metrics improved but attribution is weak."]
    reasons.append(f"Signature rung {sig.rung}.")
    return "in_progress", reasons


def run_shadow(events: list[Union[dict, EfficastEvent]], *, expected_units: Optional[dict] = None) -> ShadowReport:
    rec = reconcile(events, expected_units=expected_units)
    by_cid: "OrderedDict[str, list[EfficastEvent]]" = OrderedDict()
    for ev in rec.accepted:
        by_cid.setdefault(ev.correlation_id, []).append(ev)

    conditions = _conveyor_conditions()
    reports: list[ShadowIncidentReport] = []
    for cid, evs in by_cid.items():
        obs = _observations_from(evs)
        sig = score_observations(conditions, obs, required_stable=_REQUIRED_STABLE)
        trust = _sensor_trust(evs)
        # comparability: the bundle is comparable by construction; reflect the product + sensor status only
        product = next((e.product for e in evs if isinstance(e, ProductionOrderContext)), _NORMAL_CONTEXT["product"])
        observed_ctx = {**_NORMAL_CONTEXT, "product": product,
                        "sensor_health": "ok" if trust == "trusted" else "degraded"}
        comp = classify_context(_NORMAL_CONTEXT, observed_ctx)
        proposed, reasons = _propose(sig, comp["classification"], trust, obs)
        actual = next((e.decision_type for e in evs if isinstance(e, RecoveryDecisionPublication)), None)
        agreement = (proposed == actual) if actual is not None else None
        reports.append(ShadowIncidentReport(
            correlation_id=cid, proposed_disposition=proposed, actual_outcome=actual, agreement=agreement,
            signature_rung=sig.rung, alignment=sig.alignment, comparability=comp["classification"],
            sensor_trust=trust, observed_cycles=sig.observed_cycles, reasons=reasons,
        ))
    return ShadowReport(incidents=reports, reconciliation=rec, writes_performed=0)
