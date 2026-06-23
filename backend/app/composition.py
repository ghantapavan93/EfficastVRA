"""Composition root — the one place the object graph is assembled from configuration.

Driving adapters (the HTTP API, the CLI, the demo) ask the composition root for a wired service
instead of constructing ports themselves. So "which adapter / which model" is a single decision in a
single file (the essence of hexagonal architecture). To take this prototype to a real deployment you
change *only* this module:

  • `build_port`     → return `EfficastApiPort(authorized_client)` instead of `SyntheticEfficastPort`
  • `build_reasoning`→ return a hosted ReasoningProvider when credentials exist (deterministic fallback)

Nothing in the domain, evaluator, gateway, workflow, or UI changes.
"""

from __future__ import annotations

from sqlmodel import Session

from app.adapters.synthetic import SyntheticEfficastPort
from app.ports import EfficastPort, ReasoningProvider
from app.reasoning import get_reasoning_provider
from app.workflow.recovery_service import RecoveryService


def build_port(session: Session) -> EfficastPort:
    """The host-MES adapter. Swap for `EfficastApiPort(client)` in an authorized real deployment."""
    return SyntheticEfficastPort(session)


def build_reasoning() -> ReasoningProvider:
    """The reasoning provider (deterministic by default; a hosted model when configured)."""
    return get_reasoning_provider()


def build_recovery_service(session: Session) -> RecoveryService:
    """Assemble the orchestrator with its ports — the wiring every driving adapter shares."""
    return RecoveryService(session, port=build_port(session), reasoning=build_reasoning())
