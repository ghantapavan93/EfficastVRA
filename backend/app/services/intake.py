"""Recovery Mission Intake — Bring-Your-Own-Plant-Data.

The front of the funnel for the Recovery Mission Engine: take a messy plant export (CSV / JSON / JSONL),
detect its schema, **propose** a mapping onto the Efficast Recovery Data Contract (the AI/heuristic proposes;
a human confirms), produce a **Data Readiness Report**, and **reconstruct** the incident timeline with each
fact tagged by provenance (observed / derived / human / ai_interpretation / missing).

Governed by design: this module only *proposes and reports*. It never decides recovery and never controls a
machine — the deterministic qualification layer (comparability, evidence, sensor-trust, disposition) owns the
verdict downstream. Everything here is read-only analysis over uploaded bytes.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# ── Canonical targets (Efficast Recovery Data Contract fields) + synonyms for heuristic mapping ──────────
# (event_type, canonical_field, kind, [synonyms])
CANONICAL: list[tuple[str, str, str, list[str]]] = [
    ("asset", "source_id", "id", ["machine", "machine_code", "machine_id", "asset", "asset_id", "equipment", "equipment_id", "line", "line_id", "device"]),
    ("event", "source_timestamp", "time", ["timestamp", "time", "event_time", "ts", "datetime", "recorded_at", "occurred_at", "date_time"]),
    ("telemetry", "metric", "category", ["metric", "signal", "parameter", "tag", "measurement", "measurement_name", "channel"]),
    ("telemetry", "value", "number", ["value", "reading", "measurement_value", "vibration", "vibration_rms", "temperature", "temp", "cycle_time", "scrap_pct", "motor_current", "pressure"]),
    ("telemetry", "unit", "category", ["unit", "uom", "units"]),
    ("machine_event", "event_code", "category", ["fault", "fault_code", "alarm", "alarm_code", "event_code", "code", "error", "error_code"]),
    ("machine_event", "severity", "category", ["severity", "level", "priority"]),
    ("production_cycle", "cycle_index", "number", ["cycle", "cycle_index", "cycle_no", "cycle_number", "cycle_count", "seq"]),
    ("production_cycle", "good_count", "number", ["good", "good_count", "ok_count", "passed", "good_parts"]),
    ("production_cycle", "scrap_count", "number", ["scrap", "scrap_count", "reject", "rejects", "defects", "defect_count"]),
    ("production_order", "order_id", "id", ["order", "order_id", "po", "production_order", "wo", "work_order", "work_order_id", "job"]),
    ("production_order", "product", "category", ["product", "sku", "part", "part_number", "item"]),
    ("intervention", "kind", "category", ["intervention", "action", "repair", "maintenance_type", "work_type", "task"]),
    ("quality_check", "result", "category", ["result", "status", "pass_fail", "inspection_result", "outcome", "quality_result"]),
    ("lot_trace", "lot_id", "id", ["lot", "batch", "batch_number", "lot_id", "lot_no", "lot_number"]),
    ("approval", "decided_by", "category", ["approver", "approved_by", "quality_manager", "authorizer", "signoff", "approval_by"]),
    ("operator_observation", "operator", "category", ["operator", "author", "user", "technician", "recorded_by", "note_by"]),
    ("sensor_health", "status", "category", ["sensor_status", "sensor_health", "calibration", "health"]),
]

_BLOCKING_FIELDS = {("event", "source_timestamp"), ("asset", "source_id")}  # cannot reconstruct without these
_TS_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M")


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _tokens(name: str) -> set[str]:
    return {t for t in _norm(name).split("_") if t}


def _looks_number(samples: list[str]) -> bool:
    ok = 0
    for s in samples:
        try:
            float(str(s).replace(",", ""))
            ok += 1
        except (ValueError, TypeError):
            pass
    return bool(samples) and ok / len(samples) >= 0.7


def _parse_ts(s: str) -> Optional[datetime]:
    s = str(s).strip()
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _looks_time(samples: list[str]) -> bool:
    return bool(samples) and sum(1 for s in samples if _parse_ts(s)) / len(samples) >= 0.6


def _infer_kind(samples: list[str]) -> str:
    if _looks_time(samples):
        return "time"
    if _looks_number(samples):
        return "number"
    return "category"


# ── parsing ─────────────────────────────────────────────────────────────────────────────────────────────
@dataclass
class ParsedTable:
    fmt: str
    columns: list[str]
    rows: list[dict]


def parse_content(filename: str, content: str) -> ParsedTable:
    """Detect CSV / JSON / JSONL from the filename + content and parse to columns + row dicts."""
    name = (filename or "").lower()
    text = content.strip()
    # JSON array
    if name.endswith(".json") or text.startswith("["):
        data = json.loads(text)
        rows = data if isinstance(data, list) else [data]
        rows = [r for r in rows if isinstance(r, dict)]
        cols = list({k for r in rows for k in r.keys()})
        return ParsedTable("json", cols, rows)
    # JSONL
    if name.endswith(".jsonl") or (text.startswith("{") and "\n" in text):
        rows = [json.loads(ln) for ln in text.splitlines() if ln.strip().startswith("{")]
        cols = list({k for r in rows for k in r.keys()})
        return ParsedTable("jsonl", cols, rows)
    # CSV (default)
    reader = csv.DictReader(io.StringIO(content))
    rows = [dict(r) for r in reader]
    cols = list(reader.fieldnames or (rows[0].keys() if rows else []))
    return ParsedTable("csv", cols, rows)


# ── mapping proposal ────────────────────────────────────────────────────────────────────────────────────
@dataclass
class ColumnMapping:
    column: str
    target_event: Optional[str]
    target_field: Optional[str]
    confidence: float
    kind: str
    samples: list[str]
    missing_pct: float
    note: str = ""


def _score(col_tokens: set[str], col_norm: str, synonyms: list[str]) -> float:
    best = 0.0
    for syn in synonyms:
        sn = _norm(syn)
        if col_norm == sn:
            return 1.0
        if sn in col_norm or col_norm in sn:
            best = max(best, 0.82)
        st = _tokens(syn)
        inter = col_tokens & st
        if inter:
            best = max(best, 0.5 + 0.3 * len(inter) / max(len(col_tokens | st), 1))
    return best


def propose_mapping(table: ParsedTable) -> list[ColumnMapping]:
    out: list[ColumnMapping] = []
    rows = table.rows
    n = max(1, len(rows))
    for col in table.columns:
        vals = [r.get(col) for r in rows]
        nonnull = [v for v in vals if v not in (None, "", "null")]
        samples = [str(v) for v in nonnull[:5]]
        kind = _infer_kind([str(v) for v in nonnull[:30]])
        col_norm, col_tokens = _norm(col), _tokens(col)
        best_target: Optional[tuple[str, str, str]] = None
        best_conf = 0.0
        for ev, fld, fkind, syns in CANONICAL:
            sc = _score(col_tokens, col_norm, syns)
            # type compatibility nudges
            if sc > 0 and fkind == "number" and kind != "number":
                sc *= 0.5
            if sc > 0 and fkind == "time" and kind != "time":
                sc *= 0.4
            if sc > best_conf:
                best_conf, best_target = sc, (ev, fld, fkind)
        mapped = best_target if best_conf >= 0.4 else None
        out.append(ColumnMapping(
            column=col,
            target_event=mapped[0] if mapped else None,
            target_field=mapped[1] if mapped else None,
            confidence=round(best_conf if mapped else 0.0, 2),
            kind=kind,
            samples=samples,
            missing_pct=round(100 * (1 - len(nonnull) / n), 1),
            note="" if mapped else "no confident canonical match — confirm or leave unmapped",
        ))
    return out


# ── data readiness ──────────────────────────────────────────────────────────────────────────────────────
@dataclass
class ReadinessReport:
    score: int
    verdict: str
    ready: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    dimensions: list[dict] = field(default_factory=list)


def assess_readiness(table: ParsedTable, mappings: list[ColumnMapping]) -> ReadinessReport:
    mapped = {(m.target_event, m.target_field): m for m in mappings if m.target_event}
    has = lambda ev, fld: (ev, fld) in mapped  # noqa: E731
    ready, warn, blocked, dims = [], [], [], []

    def dim(name: str, status: str, detail: str):
        dims.append({"name": name, "status": status, "detail": detail})

    # completeness
    avg_missing = round(sum(m.missing_pct for m in mappings) / max(1, len(mappings)), 1)
    if avg_missing <= 5:
        ready.append(f"Completeness high ({100 - avg_missing:.0f}%)"); dim("Completeness", "pass", f"{100 - avg_missing:.0f}% populated")
    elif avg_missing <= 20:
        warn.append(f"{avg_missing:.0f}% of values are missing across columns"); dim("Completeness", "warn", f"{avg_missing:.0f}% missing")
    else:
        blocked.append(f"Too sparse — {avg_missing:.0f}% missing"); dim("Completeness", "fail", f"{avg_missing:.0f}% missing")

    # timestamp continuity
    if has("event", "source_timestamp"):
        tcol = mapped[("event", "source_timestamp")].column
        ts = [_parse_ts(r.get(tcol, "")) for r in table.rows]
        ts = [t for t in ts if t]
        ooo = sum(1 for a, b in zip(ts, ts[1:]) if b < a)
        if ts and ooo == 0:
            ready.append("Timestamps synchronized and ordered"); dim("Timestamp continuity", "pass", f"{len(ts)} ordered events")
        elif ts:
            warn.append(f"{ooo} out-of-order timestamps (reconciler will re-order)"); dim("Timestamp continuity", "warn", f"{ooo} out-of-order")
        else:
            blocked.append("Timestamp column could not be parsed"); dim("Timestamp continuity", "fail", "unparseable")
    else:
        blocked.append("No timestamp mapped — the incident cannot be reconstructed"); dim("Timestamp continuity", "fail", "missing")

    # asset linkage
    dim("Asset linkage", "pass" if has("asset", "source_id") else "fail", "machine identified" if has("asset", "source_id") else "no machine id")
    (ready if has("asset", "source_id") else blocked).append("Machine / asset identified" if has("asset", "source_id") else "No machine identifier mapped")

    # linkage / evidence presence
    checks = [
        (has("machine_event", "event_code"), "Fault events present", "No fault/event column — recurrence can't be detected", "Fault linkage"),
        (has("production_cycle", "cycle_index"), "Production cycles linked", "No cycle index — stable-cycle counting is limited", "Cycle linkage"),
        (has("quality_check", "result"), "Quality checks available", "Quality inspection data not provided", "Quality"),
        (has("approval", "decided_by"), "Approval records present", "Quality/authorization approval missing — verification will be blocked", "Authorization"),
        (has("lot_trace", "lot_id"), "Lot traceability linked", "No lot data — lot-at-risk exposure can't be computed", "Lot traceability"),
    ]
    for ok, good, bad, dname in checks:
        if ok:
            ready.append(good); dim(dname, "pass", good)
        else:
            (blocked if dname == "Authorization" else warn).append(bad); dim(dname, "fail" if dname == "Authorization" else "warn", bad)

    # score
    npass = sum(1 for d in dims if d["status"] == "pass")
    score = max(0, min(100, round(100 * npass / max(1, len(dims)) - len(blocked) * 6)))
    verdict = "blocked" if blocked else ("ready" if score >= 70 else "warn")
    return ReadinessReport(score=score, verdict=verdict, ready=ready, warnings=warn, blocked=blocked, dimensions=dims)


# ── incident reconstruction ─────────────────────────────────────────────────────────────────────────────
@dataclass
class TimelineEntry:
    at: Optional[str]
    label: str
    kind: str  # observed | derived | human | ai_interpretation | missing | contradiction
    detail: str = ""


def reconstruct(table: ParsedTable, mappings: list[ColumnMapping]) -> dict:
    mapped = {(m.target_event, m.target_field): m for m in mappings if m.target_event}
    tcol = mapped.get(("event", "source_timestamp"))
    fcol = mapped.get(("machine_event", "event_code"))
    ccol = mapped.get(("production_cycle", "cycle_index"))
    entries: list[TimelineEntry] = []

    rows = table.rows
    if tcol:
        rows = sorted(rows, key=lambda r: _parse_ts(r.get(tcol.column, "")) or datetime.min)

    fault_rows = []
    if fcol:
        for r in rows:
            code = str(r.get(fcol.column, "")).strip()
            if code and code.lower() not in ("none", "ok", "0", "nan", "null"):
                ts = _parse_ts(r.get(tcol.column, "")) if tcol else None
                cyc = r.get(ccol.column) if ccol else None
                fault_rows.append((ts, code, cyc))
                entries.append(TimelineEntry(
                    at=ts.isoformat() if ts else None,
                    label=f"Fault {code} detected" + (f" at cycle {cyc}" if cyc else ""),
                    kind="observed", detail="From the uploaded machine-event data."))

    # A fault that appears AFTER stable operation began = the recovery did not hold (a false closure).
    relapse = False
    if fault_rows:
        cyc0 = fault_rows[0][2]
        try:
            relapse = int(float(cyc0)) > 1
        except (TypeError, ValueError):
            relapse = len(fault_rows) >= 2
    if relapse:
        last = fault_rows[-1]
        entries.append(TimelineEntry(at=last[0].isoformat() if last[0] else None,
            label=f"Recovery did not sustain — {last[1]} returned" + (f" at cycle {last[2]}" if last[2] else ""),
            kind="derived", detail="A monitored fault returned after an apparent recovery; closing the work order here would have been a false closure."))
        entries.append(TimelineEntry(at=None,
            label="The first intervention likely addressed a symptom, not the root cause.",
            kind="ai_interpretation", detail="AI interpretation — NOT the official root-cause determination; a human reliability engineer decides."))
    elif fault_rows:
        entries.append(TimelineEntry(at=None, label="A fault is present but no relapse pattern was detected.",
            kind="derived", detail="Review whether this fault preceded or followed the intervention."))

    # missing evidence
    if ("quality_check", "result") not in mapped:
        entries.append(TimelineEntry(at=None, label="Quality inspection evidence is missing.", kind="missing",
            detail="Verification cannot complete without quality results."))
    if ("approval", "decided_by") not in mapped:
        entries.append(TimelineEntry(at=None, label="Quality/authorization approval is missing.", kind="missing",
            detail="Release is prohibited until an authorized approval is recorded."))

    summary = (
        "The incident can be reconstructed, but verification cannot yet complete — "
        + ", ".join([e.label.rstrip(".").lower() for e in entries if e.kind == "missing"]) + "."
        if any(e.kind == "missing" for e in entries)
        else "The incident timeline was reconstructed from the uploaded evidence."
    )
    return {
        "summary": summary,
        "entries": [vars(e) for e in entries],
        "fault_count": len(fault_rows),
        "false_closure_detected": relapse,
    }


# ── orchestration ───────────────────────────────────────────────────────────────────────────────────────
def analyze_upload(filename: str, content: str) -> dict:
    """One call: parse → propose mapping → readiness → reconstruct. The user confirms the mapping next."""
    table = parse_content(filename, content)
    mappings = propose_mapping(table)
    readiness = assess_readiness(table, mappings)
    reconstruction = reconstruct(table, mappings)
    mapped_n = sum(1 for m in mappings if m.target_event)
    return {
        "filename": filename,
        "format": table.fmt,
        "row_count": len(table.rows),
        "column_count": len(table.columns),
        "mapped_count": mapped_n,
        "mappings": [vars(m) for m in mappings],
        "readiness": vars(readiness),
        "reconstruction": reconstruction,
        "basis": ("AI/heuristic proposes the mapping; a human confirms it. Readiness + reconstruction are "
                  "deterministic and advisory — the qualification verdict is decided downstream, never here."),
    }
