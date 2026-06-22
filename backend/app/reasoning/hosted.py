"""Optional hosted reasoning provider (Anthropic-compatible Messages API).

Enriches *narrative* fields only; the structured, safety-relevant outputs (contract spec, violated
keys, recommendations, permissions) always come from the deterministic provider. Any error — missing
key, network failure, bad response — falls back to deterministic output, so the demo never depends on
a model endpoint.
"""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.domain.models import Incident, RecoveryContract
from app.reasoning.deterministic import DeterministicReasoningProvider
from app.services.evaluator import EvaluationResult

_settings = get_settings()


class HostedReasoningProvider(DeterministicReasoningProvider):
    id = "HostedReasoningProvider"
    prompt_version = "hosted-1"

    def __init__(self) -> None:
        self.base_url = _settings.reasoning_base_url or "https://api.anthropic.com"
        self.model = _settings.reasoning_model
        self.api_key = _settings.reasoning_api_key

    def _complete(self, system: str, prompt: str) -> str | None:
        try:
            resp = httpx.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 300,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=20.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        except Exception:
            return None  # graceful fallback

    def explain_recovery_failure(self, *, contract: RecoveryContract, result: EvaluationResult) -> dict:
        base = super().explain_recovery_failure(contract=contract, result=result)
        text = self._complete(
            system=("You are a calm, precise manufacturing reliability assistant. One sentence, no "
                    "drama. You never instruct anyone to control a machine."),
            prompt=(f"Recovery contract violated. Violated conditions: {result.violated_keys}. "
                    "Write one calm sentence explaining that completed work did not prove recovery."),
        )
        if text:
            base["detail"] = text.strip()
        return base

    def generate_handoff_summary(self, *, session, incident: Incident) -> dict:
        base = super().generate_handoff_summary(session=session, incident=incident)
        text = self._complete(
            system="You write terse, factual shift-handoff notes for plant supervisors.",
            prompt=f"Summarise in one sentence: {base['summary']}",
        )
        if text:
            base["summary"] = text.strip()
        return base
