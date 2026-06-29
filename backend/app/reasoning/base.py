"""Provider-neutral reasoning interface."""

from __future__ import annotations

import abc
from dataclasses import dataclass

from sqlmodel import Session

from app.domain.contract import RecoveryContractSpec
from app.domain.models import Incident, Intervention, RecoveryContract
from app.services.evaluator import EvaluationResult

# Maintenance interventions the agent may *recommend* (a human accepts). This catalog is the safety
# bound on the AI diagnosis: a hosted model's recommendation is rejected unless it names one of these,
# so no model output can ever propose a physical machine-control action. None of these is machine control.
SAFE_INTERVENTION_KINDS: frozenset[str] = frozenset({
    "coupling_alignment", "bearing_replacement", "lubrication", "belt_tension",
    "sensor_recalibration", "fastener_torque", "seal_replacement", "filter_replacement",
    "alignment_check", "inspection",
})


@dataclass
class Diagnosis:
    """The agent's advisory diagnosis of an alert. Informs reasoning traces + a human-accepted proposal;
    it never decides recovery and never grants permissions (the deterministic verifier owns closure)."""

    degradation_kind: str
    classification_rationale: str
    root_causes: list[dict]  # [{cause, likelihood ∈ primary|secondary|latent|watch, basis}]
    recommended_kind: str    # always ∈ SAFE_INTERVENTION_KINDS
    recommended_title: str
    recommended_description: str
    recommended_hypothesis: str
    contingency: dict        # {kind ∈ SAFE_INTERVENTION_KINDS, note}
    summary: str
    diagnostic_confidence: float
    source: str = "deterministic"  # "deterministic" | "hosted:<model>" — surfaced in the reasoning trace


class ReasoningProvider(abc.ABC):
    """Capabilities the agent layer needs. Implementations must not own state or grant permissions."""

    id: str = "reasoning"
    prompt_version: str = "rp-1"

    def diagnose_alert(
        self, *, incident: Incident, snapshot, signals: dict, retrieved: list[dict], history: dict
    ) -> Diagnosis:
        """Advisory diagnosis of an alert: name the degradation, rank root causes, recommend a
        maintenance intervention (from ``SAFE_INTERVENTION_KINDS``) for a human to accept. Concrete here
        (a conservative, model-free default) so every provider has a safe baseline; rich providers override.
        The deterministic recovery evaluator — never this — decides whether recovery actually held."""
        return Diagnosis(
            degradation_kind="degradation_observed",
            classification_rationale="Elevated readings indicate a developing fault; cause not yet localised.",
            root_causes=[{"cause": "Undetermined — pending diagnosis", "likelihood": "primary",
                          "basis": "alert signals"}],
            recommended_kind="inspection",
            recommended_title="Diagnostic inspection",
            recommended_description="Inspect the affected subsystem to localise the fault before intervening.",
            recommended_hypothesis="A developing fault requires localisation before intervention.",
            contingency={"kind": "inspection", "note": "Re-inspect if symptoms persist."},
            summary="Developing fault detected; inspection recommended before intervention.",
            diagnostic_confidence=0.3,
            source="deterministic",
        )

    @abc.abstractmethod
    def extract_recovery_requirements(
        self, *, incident: Incident, intervention: Intervention, retrieved: list[dict]
    ) -> RecoveryContractSpec: ...

    @abc.abstractmethod
    def identify_missing_evidence(self, *, session: Session, contract: RecoveryContract) -> list[dict]: ...

    @abc.abstractmethod
    def compare_historical_interventions(self, *, session: Session, incident: Incident) -> dict: ...

    @abc.abstractmethod
    def detect_document_conflicts(
        self, *, session: Session, query: str, machine_model: str, component: str
    ) -> dict: ...

    @abc.abstractmethod
    def explain_recovery_failure(
        self, *, contract: RecoveryContract, result: EvaluationResult
    ) -> dict: ...

    @abc.abstractmethod
    def generate_handoff_summary(self, *, session: Session, incident: Incident) -> dict: ...
