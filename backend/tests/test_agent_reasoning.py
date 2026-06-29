"""The agent's advisory diagnosis — deterministic baseline + the hosted (Claude) path with strict
validation, safe-catalog binding, and graceful fallback. These prove the 'real AI' reasoning path
end-to-end WITHOUT a live API key, by injecting a fake model response.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from app.reasoning.base import SAFE_INTERVENTION_KINDS
from app.reasoning.deterministic import DeterministicReasoningProvider
from app.reasoning.hosted import HostedReasoningProvider


def _snap():
    return SimpleNamespace(code="CDX-220-07", model="CDX-220", vibration=7.2, temperature=78.0,
                           cycle_time=2.6, scrap_pct=4.1, fault_code="F27")


def _incident():
    return SimpleNamespace(machine_id="MCH-CONV-04", fault_code="F27")


_HIST = {"match": True, "historical_incident_id": "INC-1990",
         "similarity": "Same fault on a sibling drive.", "citations": []}


def _hosted_returning(monkeypatch, payload):
    h = HostedReasoningProvider()
    monkeypatch.setattr(h, "_complete", lambda system, prompt, **kw: payload)
    return h


# ── deterministic baseline keeps the demo reproducible ─────────────────────────────────────────
def test_deterministic_diagnose_reproduces_demo():
    dx = DeterministicReasoningProvider().diagnose_alert(
        incident=_incident(), snapshot=_snap(), signals={"motor_replaced_days_ago": 9},
        retrieved=[], history=_HIST)
    assert dx.degradation_kind == "mechanical_drivetrain_fault"
    assert dx.recommended_kind == "coupling_alignment"
    assert dx.recommended_kind in SAFE_INTERVENTION_KINDS
    assert dx.source == "deterministic"
    assert dx.diagnostic_confidence == 0.7
    assert any(r["likelihood"] == "latent" for r in dx.root_causes)  # bearing latent risk from history


# ── hosted path: the model genuinely drives the diagnosis when its output is valid ─────────────
def test_hosted_diagnose_uses_model_output_when_valid(monkeypatch):
    payload = json.dumps({
        "degradation_kind": "lubrication_starvation",
        "classification_rationale": "Temperature rise with stable vibration suggests inadequate lubrication.",
        "root_causes": [{"cause": "Grease path blocked", "likelihood": "primary", "basis": "temp trend"}],
        "recommended_kind": "lubrication", "recommended_title": "Re-lubricate drive bearing",
        "recommended_description": "Purge and re-grease the drive-end bearing.",
        "recommended_hypothesis": "Lubrication starvation raised bearing temperature.",
        "contingency": {"kind": "bearing_replacement", "note": "Replace if temperature persists."},
        "summary": "Likely lubrication starvation; re-grease and verify.",
        "diagnostic_confidence": 0.66,
    })
    dx = _hosted_returning(monkeypatch, payload).diagnose_alert(
        incident=_incident(), snapshot=_snap(), signals={}, retrieved=[], history=_HIST)
    assert dx.degradation_kind == "lubrication_starvation"
    assert dx.recommended_kind == "lubrication"
    assert dx.root_causes[0]["cause"] == "Grease path blocked"
    assert dx.source.startswith("hosted:")
    assert 0.0 <= dx.diagnostic_confidence <= 1.0


# ── safety bound: a model can NEVER surface a machine-control action ────────────────────────────
def test_hosted_diagnose_rejects_machine_control_recommendation(monkeypatch):
    payload = json.dumps({
        "degradation_kind": "drivetrain_fault", "classification_rationale": "x",
        "root_causes": [{"cause": "y", "likelihood": "primary", "basis": "z"}],
        "recommended_kind": "machine_restart",          # NOT in the safe catalog
        "recommended_title": "Restart the machine", "recommended_description": "Power-cycle the drive.",
        "recommended_hypothesis": "h", "contingency": {"kind": "machine_stop", "note": "n"},
        "summary": "s", "diagnostic_confidence": 0.9,
    })
    dx = _hosted_returning(monkeypatch, payload).diagnose_alert(
        incident=_incident(), snapshot=_snap(), signals={"motor_replaced_days_ago": 9},
        retrieved=[], history=_HIST)
    assert dx.recommended_kind in SAFE_INTERVENTION_KINDS
    assert dx.recommended_kind == "coupling_alignment"   # fell back to the deterministic safe action
    assert dx.contingency["kind"] in SAFE_INTERVENTION_KINDS
    assert "machine" not in dx.recommended_kind


# ── graceful fallback: model/key/network failure → deterministic diagnosis, demo never breaks ──
def test_hosted_diagnose_falls_back_on_model_failure(monkeypatch):
    h = HostedReasoningProvider()
    monkeypatch.setattr(h, "_complete", lambda system, prompt, **kw: None)
    dx = h.diagnose_alert(incident=_incident(), snapshot=_snap(),
                          signals={"motor_replaced_days_ago": 9}, retrieved=[], history=_HIST)
    assert dx.source == "deterministic"
    assert dx.degradation_kind == "mechanical_drivetrain_fault"


def test_hosted_diagnose_falls_back_on_malformed_json(monkeypatch):
    dx = _hosted_returning(monkeypatch, "sorry, I cannot produce JSON").diagnose_alert(
        incident=_incident(), snapshot=_snap(), signals={}, retrieved=[], history=_HIST)
    assert dx.source == "deterministic"


# ── defensive coercion: caps, clamps, and normalizes sloppy model output ───────────────────────
def test_hosted_diagnose_caps_and_clamps(monkeypatch):
    payload = json.dumps({
        "degradation_kind": "x" * 200, "classification_rationale": "r",
        "root_causes": [{"cause": "c", "likelihood": "bogus", "basis": "b"}],
        "recommended_kind": "inspection", "recommended_title": "t", "recommended_description": "d",
        "recommended_hypothesis": "h", "contingency": {"kind": "inspection", "note": "n"},
        "summary": "s", "diagnostic_confidence": 9.9,
    })
    dx = _hosted_returning(monkeypatch, payload).diagnose_alert(
        incident=_incident(), snapshot=_snap(), signals={}, retrieved=[], history={})
    assert len(dx.degradation_kind) <= 60            # capped
    assert dx.diagnostic_confidence == 1.0           # clamped to [0,1]
    assert dx.root_causes[0]["likelihood"] == "secondary"  # bogus likelihood normalized
