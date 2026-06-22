"""Provider-neutral reasoning interface."""

from __future__ import annotations

import abc

from sqlmodel import Session

from app.domain.contract import RecoveryContractSpec
from app.domain.models import Incident, Intervention, RecoveryContract
from app.services.evaluator import EvaluationResult


class ReasoningProvider(abc.ABC):
    """Capabilities the agent layer needs. Implementations must not own state or grant permissions."""

    id: str = "reasoning"
    prompt_version: str = "rp-1"

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
