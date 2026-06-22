"""Action taxonomy, tool descriptor, and the gateway execution context.

The four action classes and the explicit PROHIBITED set are the OT-safety core: no tool may ever be
registered with a name in :data:`PROHIBITED_ACTIONS`, and a proposal naming one is denied + audited.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel

from app.adapters.efficast_port import EfficastPort
from app.auth import Principal
from app.domain.enums import ActionClass, Role
from sqlmodel import Session

# Actions that must never exist as tools or endpoints — physical/safety control.
PROHIBITED_ACTIONS: frozenset[str] = frozenset({
    "machine_start",
    "machine_stop",
    "machine_restart",
    "plc_modification",
    "setpoint_modification",
    "alarm_bypass",
    "interlock_bypass",
    "loto_confirmation",
    "lockout_tagout_confirmation",
    "safety_certification",
    "automatic_quality_release",
    "model_controlled_incident_closure",
})


@dataclass
class ToolContext:
    session: Session
    port: EfficastPort
    reasoning: object  # ReasoningProvider (avoid import cycle)
    principal: Principal
    correlation_id: str
    incident_id: Optional[str]
    input: BaseModel
    idempotency_key: Optional[str] = None


@dataclass
class ToolSpec:
    name: str
    action_class: ActionClass
    allowed_roles: frozenset[Role]
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    is_write: bool
    handler: Callable[[ToolContext], BaseModel]
    summary: str = ""
    # optional extra deterministic policy gate: returns (ok, reason)
    policy: Optional[Callable[[ToolContext], tuple[bool, str]]] = None
    requires_human: bool = False  # the actor must be a human of an allowed role


ALL_ROLES = frozenset({Role.SUPERVISOR, Role.TECHNICIAN, Role.QUALITY_ENGINEER, Role.PLANT_ADMIN})
READ_ROLES = ALL_ROLES | frozenset({Role.AGENT, Role.SYSTEM})


class ToolError(Exception):
    """Explicit, typed tool failure (maps to a 4xx, audited as a tool error)."""

    def __init__(self, message: str, *, code: str = "tool_error"):
        super().__init__(message)
        self.code = code


class ActionDenied(Exception):
    """A gateway pipeline stage refused the action."""

    def __init__(self, message: str, *, stage: str, code: str = "denied"):
        super().__init__(message)
        self.stage = stage
        self.code = code
