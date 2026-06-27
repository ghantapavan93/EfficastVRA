"""Integration reconciliation — make a noisy real-world event stream safe to evaluate.

Deterministic, in-memory reconciliation over enveloped events: dedup (idempotency_key — covers replayed
webhooks and "external success / lost response"), ordering (re-emit by ``source_timestamp``), lateness,
clock drift (|ingestion − source|), unit mismatch, mapping-version change, partial/suspect data, and
unknown/unmappable events. It NEVER drops information silently: every dropped duplicate and every
questionable event is recorded as an ``Anomaly`` with its idempotency_key.

The persistent counterpart (the gateway's ``IdempotencyRecord`` + transactional outbox + hash-chained
audit) already exists for live writes; this is the read-side reconciler used by replay + shadow.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional, Union

from pydantic import ValidationError

from app.integration.efficast.contract import (
    DataQuality,
    EfficastEvent,
    TelemetryObservation,
    parse_event,
)

# expected canonical units per telemetry metric (a tiny mapping registry; PROTOTYPE_ASSUMPTION)
DEFAULT_UNITS: dict[str, str] = {
    "vibration_rms": "mm/s",
    "temperature": "°C",
    "cycle_time": "s",
    "scrap_pct": "%",
    "bearing_precursor": "",
}


@dataclass
class Anomaly:
    kind: str           # duplicate | out_of_order | late | clock_drift | unit_mismatch | mapping_version_change | partial_data | missing_mapping
    idempotency_key: str
    detail: str = ""
    event_type: str = ""


@dataclass
class ReconciliationResult:
    accepted: list[EfficastEvent]          # deduped, ordered by source_timestamp
    anomalies: list[Anomaly] = field(default_factory=list)
    counts: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.anomalies


def reconcile(
    events: list[Union[dict, EfficastEvent]],
    *,
    clock_drift_tol_s: float = 120.0,
    late_tolerance_s: float = 300.0,
    expected_units: Optional[dict[str, str]] = None,
) -> ReconciliationResult:
    expected_units = expected_units if expected_units is not None else DEFAULT_UNITS
    seen: set[str] = set()
    accepted: list[EfficastEvent] = []
    anomalies: list[Anomaly] = []
    mapping_versions: dict[str, str] = {}
    watermark = None  # max source_timestamp accepted so far (for out-of-order / late)

    for raw in events:
        # parse / missing-mapping
        if isinstance(raw, EfficastEvent):
            ev: EfficastEvent = raw
        else:
            try:
                ev = parse_event(raw)
            except (ValidationError, KeyError, TypeError) as e:
                anomalies.append(Anomaly("missing_mapping", str(raw.get("idempotency_key", "?") if isinstance(raw, dict) else "?"),
                                         f"unmappable event: {e}", str(raw.get("event_type", "") if isinstance(raw, dict) else "")))
                continue

        # dedup (replayed webhook / lost-response retry)
        if ev.idempotency_key in seen:
            anomalies.append(Anomaly("duplicate", ev.idempotency_key, "already ingested", ev.event_type))
            continue
        seen.add(ev.idempotency_key)

        # clock drift
        drift = abs((ev.ingestion_timestamp - ev.source_timestamp).total_seconds())
        if drift > clock_drift_tol_s:
            anomalies.append(Anomaly("clock_drift", ev.idempotency_key, f"{drift:.0f}s skew", ev.event_type))

        # ordering / lateness (relative to the running watermark)
        if watermark is not None and ev.source_timestamp < watermark:
            behind = (watermark - ev.source_timestamp).total_seconds()
            kind = "late" if behind > late_tolerance_s else "out_of_order"
            anomalies.append(Anomaly(kind, ev.idempotency_key, f"{behind:.0f}s behind watermark", ev.event_type))
        else:
            watermark = ev.source_timestamp

        # unit mismatch (telemetry only)
        if isinstance(ev, TelemetryObservation):
            exp = expected_units.get(ev.metric)
            if exp is not None and ev.unit and ev.unit != exp:
                anomalies.append(Anomaly("unit_mismatch", ev.idempotency_key, f"{ev.unit} != {exp}", ev.event_type))

        # mapping-version change (per source system)
        prev = mapping_versions.get(ev.source_system)
        if prev is not None and prev != ev.mapping_version:
            anomalies.append(Anomaly("mapping_version_change", ev.idempotency_key,
                                     f"{prev} → {ev.mapping_version}", ev.event_type))
        mapping_versions[ev.source_system] = ev.mapping_version

        # partial / suspect / stale
        if ev.data_quality != DataQuality.OK:
            anomalies.append(Anomaly("partial_data", ev.idempotency_key, ev.data_quality.value, ev.event_type))

        accepted.append(ev)

    accepted.sort(key=lambda e: e.source_timestamp)  # downstream always sees source-time order
    return ReconciliationResult(accepted=accepted, anomalies=anomalies,
                                counts=dict(Counter(a.kind for a in anomalies)))
