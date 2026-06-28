"""Per-identity fixed-window rate limiter — abuse / request-flooding protection.

In-process and best-effort: it protects a single instance and resets its windows from a monotonic
clock. Limits are PROTOTYPE_ASSUMPTIONs (env-tunable). A multi-instance deployment swaps the backing
store for Redis/Memcached behind the same ``check()`` interface so quotas are shared. This is a
throttle, never a control action — it only rejects, it never mutates domain state.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Callable


@dataclass
class RateDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    window_s: int


class RateLimiter:
    def __init__(self, *, limit: int, window_s: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.window_s = window_s
        self._clock = clock
        self._lock = Lock()
        self._buckets: dict[str, tuple[float, int]] = {}  # key → (window_start, count)

    def check(self, key: str) -> RateDecision:
        now = self._clock()
        with self._lock:
            start, count = self._buckets.get(key, (now, 0))
            if now - start >= self.window_s:  # window expired → roll a fresh one
                start, count = now, 0
            count += 1
            self._buckets[key] = (start, count)
            allowed = count <= self.limit
            remaining = max(0, self.limit - count)
            retry_after = 0 if allowed else int(self.window_s - (now - start)) + 1
            return RateDecision(allowed=allowed, limit=self.limit, remaining=remaining,
                                retry_after=retry_after, window_s=self.window_s)

    def snapshot(self) -> dict:
        with self._lock:
            return {"tracked_identities": len(self._buckets), "limit": self.limit,
                    "window_s": self.window_s}

    def reset(self) -> None:
        """Test hook — drop all windows."""
        with self._lock:
            self._buckets.clear()
