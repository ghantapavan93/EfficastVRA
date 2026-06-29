"""Optional hosted reasoning provider (Anthropic-compatible Messages API).

Enriches *narrative* fields only; the structured, safety-relevant outputs (contract spec, violated
keys, recommendations, permissions) always come from the deterministic provider. Any error — missing
key, network failure, bad response — falls back to deterministic output, so the demo never depends on
a model endpoint.
"""

from __future__ import annotations

import json

import httpx

from app.config import get_settings
from app.domain.models import Incident, RecoveryContract
from app.reasoning.base import SAFE_INTERVENTION_KINDS, Diagnosis
from app.reasoning.deterministic import DeterministicReasoningProvider
from app.services.evaluator import EvaluationResult

_settings = get_settings()

_LIKELIHOODS = {"primary", "secondary", "latent", "watch"}


def _capped_str(value, cap: int, default: str) -> str:
    if isinstance(value, (str, int, float)) and str(value).strip():
        return str(value).strip()[:cap]
    return default


class HostedReasoningProvider(DeterministicReasoningProvider):
    id = "HostedReasoningProvider"
    prompt_version = "hosted-1"

    def __init__(self) -> None:
        self.base_url = _settings.reasoning_base_url or "https://api.anthropic.com"
        self.model = _settings.reasoning_model
        self.api_key = _settings.reasoning_api_key

    def _complete(self, system: str, prompt: str, *, max_tokens: int = 300) -> str | None:
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
                    "max_tokens": max_tokens,
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

    def _complete_json(self, system: str, prompt: str, *, max_tokens: int = 700) -> dict | None:
        """Ask for strict JSON and parse it defensively (tolerates prose around the object)."""
        text = self._complete(system, prompt, max_tokens=max_tokens)
        if not text:
            return None
        try:
            obj = text[text.index("{"): text.rindex("}") + 1]
            parsed = json.loads(obj)
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, json.JSONDecodeError):
            return None

    # ── Real model-driven diagnosis (advisory) ───────────────────────────────────
    def diagnose_alert(
        self, *, incident: Incident, snapshot, signals: dict, retrieved: list[dict], history: dict
    ) -> Diagnosis:
        """Diagnose the alert with the hosted model, grounded in the live snapshot + approved manual
        excerpts + historical precedent. The output is validated against a strict shape and the safe
        intervention catalog; any missing/invalid field (or any model/parse failure) falls back to the
        deterministic diagnosis. The model never decides recovery and can never name a machine-control action."""
        det = super().diagnose_alert(
            incident=incident, snapshot=snapshot, signals=signals, retrieved=retrieved, history=history)
        excerpts = "\n".join(
            f"- {r.get('section', '')}: {r.get('excerpt', '')}" for r in (retrieved or [])[:4]
        ) or "none"
        hist_line = (history.get("similarity") if history else None) or "No comparable historical incident."
        system = (
            "You are a manufacturing reliability diagnostician for a packaging plant. You analyse a "
            "post-alert machine snapshot, approved manual excerpts, and historical precedent, then return "
            "STRICT JSON only (no prose). You NEVER instruct anyone to start, stop, restart, or reconfigure "
            "a machine; you only name a likely degradation, rank root causes, and recommend ONE maintenance "
            "intervention from the allowed list for a human to accept. A separate deterministic verifier "
            "decides whether recovery actually held — never you."
        )
        prompt = (
            f"Machine {getattr(snapshot, 'code', incident.machine_id)} "
            f"({getattr(snapshot, 'model', '')}), fault {getattr(snapshot, 'fault_code', None) or incident.fault_code}.\n"
            f"Live readings: vibration {getattr(snapshot, 'vibration', '?')} mm/s, "
            f"temp {getattr(snapshot, 'temperature', '?')}C, cycle {getattr(snapshot, 'cycle_time', '?')}s, "
            f"scrap {getattr(snapshot, 'scrap_pct', '?')}%.\n"
            f"Signals: {json.dumps(signals, default=str)}\n"
            f"Approved manual excerpts:\n{excerpts}\n"
            f"Historical precedent: {hist_line}\n"
            f"Allowed intervention kinds: {sorted(SAFE_INTERVENTION_KINDS)}\n\n"
            'Return JSON: {"degradation_kind": str, "classification_rationale": str, '
            '"root_causes": [{"cause": str, "likelihood": "primary|secondary|latent|watch", "basis": str}], '
            '"recommended_kind": one allowed kind, "recommended_title": str, "recommended_description": str, '
            '"recommended_hypothesis": str, "contingency": {"kind": one allowed kind, "note": str}, '
            '"summary": str, "diagnostic_confidence": number between 0 and 1}'
        )
        data = self._complete_json(system, prompt)
        return self._validate_diagnosis(data, det)

    def _validate_diagnosis(self, data: dict | None, det: Diagnosis) -> Diagnosis:
        """Coerce a model response into a safe ``Diagnosis``; fall back to ``det`` per-field. Crucially,
        the recommended/contingency kinds are forced into ``SAFE_INTERVENTION_KINDS`` — so even a
        compromised or hallucinating model can never surface a machine-control action."""
        if not isinstance(data, dict):
            return det

        root_causes: list[dict] = []
        for item in (data.get("root_causes") or [])[:3]:
            if not isinstance(item, dict):
                continue
            cause = _capped_str(item.get("cause"), 200, "")
            if not cause:
                continue
            likelihood = item.get("likelihood")
            root_causes.append({
                "cause": cause,
                "likelihood": likelihood if likelihood in _LIKELIHOODS else "secondary",
                "basis": _capped_str(item.get("basis"), 200, ""),
            })
        if not root_causes:
            root_causes = det.root_causes

        rec_kind = data.get("recommended_kind")
        rec_kind = rec_kind if rec_kind in SAFE_INTERVENTION_KINDS else det.recommended_kind
        cont = data.get("contingency") if isinstance(data.get("contingency"), dict) else {}
        cont_kind = cont.get("kind")
        cont_kind = cont_kind if cont_kind in SAFE_INTERVENTION_KINDS else det.contingency.get("kind", "inspection")

        try:
            confidence = float(data.get("diagnostic_confidence", det.diagnostic_confidence))
        except (TypeError, ValueError):
            confidence = det.diagnostic_confidence
        confidence = max(0.0, min(1.0, confidence))

        return Diagnosis(
            degradation_kind=_capped_str(data.get("degradation_kind"), 60, det.degradation_kind),
            classification_rationale=_capped_str(
                data.get("classification_rationale"), 280, det.classification_rationale),
            root_causes=root_causes,
            recommended_kind=rec_kind,
            recommended_title=_capped_str(data.get("recommended_title"), 90, det.recommended_title),
            recommended_description=_capped_str(
                data.get("recommended_description"), 280, det.recommended_description),
            recommended_hypothesis=_capped_str(
                data.get("recommended_hypothesis"), 220, det.recommended_hypothesis),
            contingency={"kind": cont_kind, "note": _capped_str(cont.get("note"), 200, det.contingency.get("note", ""))},
            summary=_capped_str(data.get("summary"), 280, det.summary),
            diagnostic_confidence=confidence,
            source=f"hosted:{self.model}",
        )

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
