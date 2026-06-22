"""Bounded AI reasoning.

The reasoning layer interprets manuals, extracts recovery requirements, compares history, finds
missing evidence, detects document conflicts, and writes explanations. It **never** owns state or
permissions — it returns data that deterministic code and the Agent Action Gateway then act on.

The deterministic provider carries the entire demo with no API key; a hosted provider can enrich
explanations but always falls back to deterministic output.
"""

from __future__ import annotations

from app.config import get_settings
from app.reasoning.base import ReasoningProvider
from app.reasoning.deterministic import DeterministicReasoningProvider

_settings = get_settings()


def get_reasoning_provider() -> ReasoningProvider:
    if _settings.reasoning_provider == "hosted" and _settings.reasoning_api_key:
        try:
            from app.reasoning.hosted import HostedReasoningProvider

            return HostedReasoningProvider()
        except Exception:
            return DeterministicReasoningProvider()
    return DeterministicReasoningProvider()


__all__ = ["ReasoningProvider", "DeterministicReasoningProvider", "get_reasoning_provider"]
