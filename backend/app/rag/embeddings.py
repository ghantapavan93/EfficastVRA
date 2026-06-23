"""Deterministic lexical embeddings (hashing bag-of-words → unit vector).

No ML model and no network — fully deterministic, which keeps the demo reproducible and the tests
stable. In production this module is swapped for real embeddings stored in pgvector; the
``RetrievalPort`` shape (embed + cosine) is unchanged.
"""

from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

DIM = 256
_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if len(t) > 2]


@lru_cache(maxsize=2048)
def embed(text: str) -> list[float]:
    """Cached: the agent issues many repeated/near-identical queries; recomputing is wasteful.
    The returned vector is read-only by all callers (cosine), so sharing the cached list is safe."""
    vec = [0.0] * DIM
    for tok in tokenize(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)  # noqa: S324 (non-crypto use)
        idx = h % DIM
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
