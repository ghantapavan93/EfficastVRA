"""Sanitised, enveloped event bundles for replay + shadow mode.

These are SYNTHETIC, contract-v0.1-shaped events — the honest stand-in for "real" Efficast data until a
sanitised dataset is provided. The F27 bundle mirrors the hero case: a conveyor-drive line monitored over a
verification window. ``relapse_at`` injects an F27 recurrence (a MachineEvent + a vibration spike) at a
given cycle so shadow mode proposes FAILED instead of VERIFIED. Deterministic (fixed base time; no wall clock).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.integration.efficast.contract import (
    AssetContext,
    EfficastEvent,
    Intervention,
    MachineEvent,
    ProductionOrderContext,
    QualityCheck,
    RecoveryDecisionPublication,
    SensorHealth,
    TelemetryObservation,
)

_BASE = datetime(2026, 1, 1, 8, 0, 0)
_CADENCE_S = 60
_MACHINE = "L4-CONV"


def _env(idem: str, cid: str, ts: datetime, *, data_quality: str = "OK", mapping_version: str = "0.1") -> dict:
    return {
        "source_system": "replay", "schema_version": "0.1", "mapping_version": mapping_version,
        "tenant_id": "t-demo", "plant_id": "PLANT-NS", "source_id": _MACHINE,
        "correlation_id": cid, "idempotency_key": idem,
        "source_timestamp": ts, "ingestion_timestamp": ts + timedelta(seconds=2),
        "timezone": "UTC", "data_quality": data_quality,
    }


def make_f27_bundle(*, cycles: int = 30, relapse_at: int | None = None, cid: str = "REPLAY-INC-1",
                    sensor_status: str = "trusted", product: str = "PKG-STD-12",
                    actual: str | None = None) -> list[EfficastEvent]:
    """A full verification window as enveloped events. Recovered by default; pass ``relapse_at`` to inject F27.

    ``product`` overrides the order's product (a *different* product makes conditions NOT_COMPARABLE in the
    Comparable-Conditions gate). ``actual`` overrides the published ground-truth decision_type (else: failed
    when a relapse is injected, verified otherwise) — so a scenario can model what the *plant* actually did.
    """
    out: list[EfficastEvent] = []
    out.append(AssetContext(**_env(f"{cid}-asset", cid, _BASE), machine_id=_MACHINE,
                            machine_model="CDX-220", component="drive-end bearing", line_id="L4",
                            criticality="high"))
    out.append(ProductionOrderContext(**_env(f"{cid}-order", cid, _BASE), order_id="PO-2841",
                                      product=product, machine_id=_MACHINE,
                                      quantity_total=12000, quantity_remaining=8420))
    out.append(Intervention(**_env(f"{cid}-itv", cid, _BASE), intervention_id="ITV-2",
                            kind="bearing_replacement", component="BR-6205", status="completed",
                            completed_at=_BASE))
    out.append(SensorHealth(**_env(f"{cid}-sensor", cid, _BASE), sensor_id="VIB-L4-01",
                            machine_id=_MACHINE, metric="vibration_rms", status=sensor_status,
                            last_sample_at=_BASE))

    for k in range(1, cycles + 1):
        ts = _BASE + timedelta(seconds=_CADENCE_S * k)
        faulted = relapse_at is not None and k == relapse_at
        # small deterministic per-cycle variation — a real (healthy) sensor is never perfectly flat, so the
        # Sensor Trust Gate would otherwise read constant values as a stuck/flatlined sensor.
        vib = 7.4 if faulted else round(3.10 + ((k % 5) - 2) * 0.04, 3)     # ~3.02–3.18, < 4.0
        temp = max(63.0 - 0.9 * k, 24.0)         # declining toward ambient
        ctime = 14.8 if faulted else round(12.20 + ((k % 3) - 1) * 0.06, 3)  # ~12.14–12.26
        scrap = 6.0 if faulted else round(0.90 + (k % 2) * 0.20, 3)
        prec = round(0.05 + 0.001 * k + ((k % 4) - 1.5) * 0.002, 4)         # flat-ish, with jitter
        for metric, value, unit, sid in (
            ("vibration_rms", vib, "mm/s", "VIB-L4-01"),
            ("temperature", round(temp, 1), "°C", "TMP-L4-01"),
            ("cycle_time", ctime, "s", "PLC-L4"),
            ("scrap_pct", scrap, "%", "MES-L4"),
            ("bearing_precursor", prec, "", "VIB-L4-01"),
        ):
            out.append(TelemetryObservation(**_env(f"{cid}-tel-{k}-{metric}", cid, ts),
                                            machine_id=_MACHINE, metric=metric, value=value, unit=unit,
                                            sensor_id=sid))
        if faulted:
            out.append(MachineEvent(**_env(f"{cid}-evt-{k}", cid, ts), machine_id=_MACHINE,
                                    event_code="F27", severity="high",
                                    description="Conveyor-drive fault F27 recurred"))

    out.append(QualityCheck(**_env(f"{cid}-qc", cid, _BASE + timedelta(seconds=_CADENCE_S * (cycles + 1))),
                            order_id="PO-2841", lot_id="LOT-7741",
                            result=("fail" if relapse_at else "pass"), metric="first_piece", spec="in-spec"))
    out.append(RecoveryDecisionPublication(
        **_env(f"{cid}-pub", cid, _BASE + timedelta(seconds=_CADENCE_S * (cycles + 2))),
        incident_id=cid, decision_type=(actual or ("failed" if relapse_at else "verified")),
        summary=("F27 recurred during the window" if relapse_at else "30 stable comparable cycles; quality released")))
    return out
