"""Shadow Mode Scorecard — the Tier-0 evaluation artifact for Efficast.

Runs the SAME deterministic cores the live system uses over the labeled scenario library, compares each
proposed disposition to the outcome the plant published, and reports it the way a champion/challenger shadow
deployment is judged: an agreement rate, a full confusion matrix, agreement-beyond-chance (Cohen's κ), and —
the safety headline — **false-closure detection** (a missed false closure / verifying a recovery that did not
hold is the catastrophic error and must be 0). It writes NOTHING: `writes_performed = 0`, structurally.
"""

from __future__ import annotations

from collections import Counter

from app.integration.efficast.scenarios import scenario_library
from app.integration.efficast.shadow import run_shadow

# An *active* "the recovery did not hold" verdict (as opposed to abstaining with insufficient_evidence).
_DID_NOT_HOLD = {"failed", "reopened"}


def _cohens_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Agreement beyond chance over (expected, proposed) pairs. 1.0 = perfect, 0 = chance-level."""
    n = len(pairs)
    if n == 0:
        return None
    classes = sorted({c for pair in pairs for c in pair})
    p_o = sum(1 for a, b in pairs if a == b) / n
    exp = Counter(a for a, _ in pairs)
    prop = Counter(b for _, b in pairs)
    p_e = sum((exp[c] / n) * (prop[c] / n) for c in classes)
    if p_e >= 1.0:
        return 1.0
    return round((p_o - p_e) / (1.0 - p_e), 3)


def run_scorecard() -> dict:
    scenarios = scenario_library()
    rows: list[dict] = []
    recon_totals: Counter = Counter()
    pairs: list[tuple[str, str]] = []

    for s in scenarios:
        report = run_shadow(s.events)
        inc = report.incidents[0] if report.incidents else None
        proposed = inc.proposed_disposition if inc else "unknown"
        recon_totals.update(report.reconciliation.counts)
        pairs.append((s.expected, proposed))
        did_not_hold = s.expected in _DID_NOT_HOLD
        rows.append({
            "key": s.key, "title": s.title, "description": s.description,
            "expected": s.expected, "proposed": proposed, "agree": proposed == s.expected,
            "is_false_closure": did_not_hold,                       # the recovery actually did not hold
            "flagged": proposed in _DID_NOT_HOLD,                   # we actively flagged a non-recovery
            "abstained": proposed == "insufficient_evidence",      # we declined to verify (caution)
            "caught": did_not_hold and proposed != "verified",     # we did NOT rubber-stamp it
            "false_verification": did_not_hold and proposed == "verified",  # CATASTROPHIC: verified a failure
            "signature_rung": inc.signature_rung if inc else None,
            "alignment": inc.alignment if inc else None,
            "comparability": inc.comparability if inc else None,
            "sensor_trust": inc.sensor_trust if inc else None,
            "observed_cycles": inc.observed_cycles if inc else 0,
            "reasons": inc.reasons if inc else [],
            "anomalies": dict(report.reconciliation.counts),
            "events_total": len(s.events),
            "events_accepted": len(report.reconciliation.accepted),
        })

    n = len(rows)
    positives = [r for r in rows if r["is_false_closure"]]
    tp = sum(1 for r in positives if r["flagged"])
    fn = sum(1 for r in positives if not r["flagged"])
    fp = sum(1 for r in rows if not r["is_false_closure"] and r["flagged"])
    false_verifications = sum(1 for r in rows if r["false_verification"])

    classes = sorted({r["expected"] for r in rows} | {r["proposed"] for r in rows})
    matrix = {a: {b: 0 for b in classes} for a in classes}
    for r in rows:
        matrix[r["expected"]][r["proposed"]] += 1

    return {
        "generated_for": "Efficast — Tier-0 shadow evaluation",
        "summary": {
            "scenarios": n,
            "agreement_rate": round(sum(1 for r in rows if r["agree"]) / n, 3) if n else None,
            "cohens_kappa": _cohens_kappa(pairs),
            "writes_performed": 0,
            "events_total": sum(r["events_total"] for r in rows),
            "events_accepted": sum(r["events_accepted"] for r in rows),
        },
        "false_closure": {
            "positives": len(positives),
            "caught": tp,
            "missed_catastrophic": false_verifications,  # verified a recovery that did not hold — must be 0
            "recall": round(tp / (tp + fn), 3) if (tp + fn) else None,
            "precision": round(tp / (tp + fp), 3) if (tp + fp) else None,
            "tp": tp, "fn": fn, "fp": fp,
            "note": "Positive class = the recovery did NOT actually hold. The catastrophic error is verifying "
                    "a failed recovery (missed_catastrophic) — it must be 0. Abstaining (insufficient_evidence) "
                    "is a safe non-verify, not a false alarm.",
        },
        "confusion_matrix": {"classes": classes, "matrix": matrix},
        "reconciliation_totals": dict(recon_totals),
        "scenarios": rows,
        "basis": (
            "Shadow mode runs the SAME deterministic cores the live system uses (recovery signature, "
            "comparable-conditions, sensor-trust) over labeled contract-v0.1 bundles and compares the proposed "
            "disposition to the outcome each bundle says the plant reached — writing NOTHING. Scenarios are "
            "SYNTHETIC (PROTOTYPE_ASSUMPTION); real-data agreement requires a sanitised Efficast export."
        ),
    }
