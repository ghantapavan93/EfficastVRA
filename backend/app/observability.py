"""Operational metrics — the SLIs an SRE watches (the second pillar of observability).

Logs (structured JSON + correlation IDs) and the tamper-evident audit are the first/third pillars;
this is a lightweight in-process metric registry for the second: request/error counters, latency
percentiles, and status distribution, exposed at ``GET /api/metrics``. The correlation IDs already
emitted are the trace-context seam for an OpenTelemetry exporter in production.
"""

from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_START = time.time()
_requests_total = 0
_errors_total = 0
_by_status: dict[str, int] = {}
_latencies: list[float] = []   # recent request latencies (ms), bounded ring buffer
_MAX_SAMPLES = 2000


def record_request(*, status: int, ms: float) -> None:
    global _requests_total, _errors_total
    with _lock:
        _requests_total += 1
        if status >= 500:
            _errors_total += 1
        cls = f"{status // 100}xx"
        _by_status[cls] = _by_status.get(cls, 0) + 1
        _latencies.append(ms)
        if len(_latencies) > _MAX_SAMPLES:
            del _latencies[0]


def _pct(sorted_lat: list[float], p: float) -> float:
    if not sorted_lat:
        return 0.0
    idx = min(len(sorted_lat) - 1, int(len(sorted_lat) * p))
    return round(sorted_lat[idx], 1)


def snapshot() -> dict:
    with _lock:
        total, errors = _requests_total, _errors_total
        by_status = dict(_by_status)
        lat = sorted(_latencies)
    return {
        "uptime_seconds": round(time.time() - _START, 1),
        "requests_total": total,
        "errors_total": errors,
        "error_rate": round(errors / total, 4) if total else 0.0,
        "latency_ms": {"p50": _pct(lat, 0.5), "p95": _pct(lat, 0.95), "p99": _pct(lat, 0.99)},
        "by_status": by_status,
    }
