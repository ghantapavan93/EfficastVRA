"""Labeled shadow-evaluation scenarios — the Tier-0 scorecard's ground truth.

Each scenario is a contract-v0.1 event bundle plus the outcome the *plant* actually published (``expected``).
Shadow mode runs the same deterministic cores and we compare. The set deliberately spans the disposition
space — genuine recoveries, true false-closures (relapses we must catch), and cases where we are *more
cautious than the plant* (a confounded comparison, an untrusted sensor) — plus noisy/partial feeds that
exercise reconciliation. SYNTHETIC (PROTOTYPE_ASSUMPTION): this proves the cores reach the right verdict on
known cases; real-data agreement needs a sanitised Efficast export.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.integration.efficast.contract import DataQuality, EfficastEvent, TelemetryObservation
from app.integration.efficast.fixtures import make_f27_bundle


@dataclass
class ShadowScenario:
    key: str
    title: str
    description: str
    expected: str  # the outcome the plant actually published (ground truth)
    events: list[EfficastEvent]


def _with_duplicates(events: list[EfficastEvent]) -> list[EfficastEvent]:
    """Append a couple of replayed (duplicate idempotency_key) telemetry events — reconciliation must dedup."""
    tels = [e for e in events if isinstance(e, TelemetryObservation)]
    dups = [tels[i].model_copy() for i in (5, 12) if i < len(tels)]
    return events + dups


def _flag_suspect(events: list[EfficastEvent], *, n: int = 2) -> list[EfficastEvent]:
    """Mark a few scrap samples SUSPECT at ingestion — reconciliation flags partial_data but still evaluates."""
    out: list[EfficastEvent] = []
    flagged = 0
    for e in events:
        if isinstance(e, TelemetryObservation) and e.metric == "scrap_pct" and flagged < n:
            out.append(e.model_copy(update={"data_quality": DataQuality.SUSPECT}))
            flagged += 1
        else:
            out.append(e)
    return out


def scenario_library() -> list[ShadowScenario]:
    return [
        ShadowScenario(
            "genuine_recovery", "Genuine recovery",
            "30 stable, comparable, trusted cycles after a drive-end bearing replacement.",
            "verified", make_f27_bundle(cycles=30, cid="SC-GENUINE")),
        ShadowScenario(
            "false_closure_mid", "False closure — relapse at cycle 17",
            "Work order completed and early cycles looked recovered; F27 recurs at cycle 17. The case the "
            "thesis exists for.",
            "failed", make_f27_bundle(cycles=30, relapse_at=17, cid="SC-RELAPSE-MID")),
        ShadowScenario(
            "false_closure_early", "False closure — early relapse",
            "F27 recurs at cycle 6 — the recovery never held.",
            "failed", make_f27_bundle(cycles=30, relapse_at=6, cid="SC-RELAPSE-EARLY")),
        ShadowScenario(
            "confounded_conditions", "More cautious than the plant — confounded conditions",
            "The plant published VERIFIED, but the window ran on a different product, so the apparent recovery "
            "can't be attributed to the intervention. We abstain.",
            "verified", make_f27_bundle(cycles=30, product="PKG-WIDE-20", cid="SC-CONFOUND")),
        ShadowScenario(
            "untrusted_sensor", "More cautious than the plant — untrusted sensor",
            "The plant closed it; our Sensor-Trust gate flags the vibration sensor as untrusted, so a hard "
            "condition can't be satisfied. We abstain.",
            "verified", make_f27_bundle(cycles=30, sensor_status="untrusted", cid="SC-UNTRUSTED")),
        ShadowScenario(
            "noisy_stream", "Noisy stream — duplicated webhooks",
            "A genuine recovery whose feed contains replayed/duplicated events. Reconciliation dedups them "
            "before anything is scored.",
            "verified", _with_duplicates(make_f27_bundle(cycles=30, cid="SC-NOISY"))),
        ShadowScenario(
            "partial_data", "Partial / suspect data",
            "A genuine recovery with a few out-of-range scrap samples flagged SUSPECT at ingestion — recorded, "
            "not silently dropped.",
            "verified", _flag_suspect(make_f27_bundle(cycles=30, cid="SC-PARTIAL"))),
    ]
