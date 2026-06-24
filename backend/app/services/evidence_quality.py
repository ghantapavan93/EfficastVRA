"""Evidence quality — not all evidence is equally trustworthy.

The deterministic evaluator already gates closure on *validated* evidence. This layer adds **how strong**
each piece is, so the UI and the provenance record never present a stale technician note as equal to a
fresh instrument reading. It is a GRADE-style hierarchy of evidence (direct/empirical outranks inferred/
secondary): a direct sensor reading > a measured human reading > a yes/no observation > a manual
reference > a system inference. Validity and freshness then discount that ceiling.

Deterministic and read-only. **Advisory weighting** — it annotates evidence; it never changes a
condition's deterministic pass/fail or the closure verdict.

References: GRADE quality-of-evidence levels (high→very-low); the hierarchy of evidence (empirical/direct
has less uncertainty than inferred/secondary). See docs/PROVENANCE.md.
"""

from __future__ import annotations

from typing import Optional

from app.domain.models import EvidenceItem, EvidenceRequirement

# Provenance tiers, highest → lowest. ``weight`` is the trust ceiling for a fresh, validated item.
TIER_META: dict[str, dict] = {
    "direct_sensor":            {"rank": 5, "weight": 1.0,  "label": "Direct instrument reading"},
    "instrumented_measurement": {"rank": 4, "weight": 0.85, "label": "Measured human reading"},
    "human_observation":        {"rank": 3, "weight": 0.6,  "label": "Technician observation"},
    "document_reference":       {"rank": 2, "weight": 0.5,  "label": "Manual / document reference"},
    "system_inferred":          {"rank": 1, "weight": 0.4,  "label": "System-inferred"},
}


def _tier(item: EvidenceItem) -> str:
    """Map an evidence item to a provenance tier from its source and whether it carries a measurement."""
    source_kind = (item.source_kind or "").strip().lower()
    has_measurement = item.value_num is not None
    if source_kind == "sensor":
        return "direct_sensor" if has_measurement else "system_inferred"
    if source_kind == "human":
        return "instrumented_measurement" if has_measurement else "human_observation"
    if source_kind == "document":
        return "document_reference"
    if source_kind == "system":
        return "system_inferred"
    return "human_observation" if (has_measurement or item.value_text) else "system_inferred"


def classify(item: EvidenceItem, requirement: Optional[EvidenceRequirement] = None) -> dict:
    """Provenance tier + trust score (0..1) for one evidence item. Validity/conflict zero the trust;
    staleness halves it. Returns the rationale and any discount flags."""
    tier = _tier(item)
    meta = TIER_META[tier]
    trust = float(meta["weight"])
    flags: list[str] = []
    status = item.status.value if item.status else None

    # Terminal-invalid (contested / rejected / expired) is NOT evidence — trust collapses to zero. But a
    # merely-SUBMITTED item awaiting validation is legitimately *pending*, not contested — discount it,
    # don't zero it (else a healthy in-progress incident reads as untrustworthy).
    if item.conflict_reason or status in ("REJECTED", "CONFLICTING", "EXPIRED"):
        flags.append("conflict" if item.conflict_reason else (status or "invalid").lower())
        trust = 0.0
    elif not item.valid:
        flags.append("pending")
        trust = round(trust * 0.5, 2)
    # Staleness discounts (but still records) the evidence, on top of the above.
    freshness_max = requirement.freshness_max_s if requirement else None
    if trust > 0 and freshness_max and item.freshness_s is not None and item.freshness_s > freshness_max:
        flags.append("stale")
        trust = round(trust * 0.5, 2)

    rationale = f"{meta['label']} (source: {item.source_kind or 'unknown'})"
    if flags:
        rationale += f"; discounted — {', '.join(flags)}"

    return {
        "evidence_id": item.id,
        "kind": item.kind.value if item.kind else None,
        "tier": tier,
        "tier_label": meta["label"],
        "rank": meta["rank"],
        "source_kind": item.source_kind,
        "source": item.source,
        "base_weight": meta["weight"],
        "trust": round(trust, 2),
        "flags": flags,
        "valid": item.valid,
        "status": item.status.value if item.status else None,
        "rationale": rationale,
    }


def summarize(classified: list[dict]) -> dict:
    """Aggregate trust across classified items — surfaces the *weakest* link, not just the average."""
    if not classified:
        return {"count": 0, "mean_trust": None, "min_trust": None, "weakest": None}
    trusts = [c["trust"] for c in classified]
    weakest = min(classified, key=lambda c: c["trust"])
    return {
        "count": len(classified),
        "mean_trust": round(sum(trusts) / len(trusts), 2),
        "min_trust": min(trusts),
        "weakest": {"evidence_id": weakest["evidence_id"], "tier": weakest["tier"],
                    "trust": weakest["trust"], "flags": weakest["flags"]},
    }
