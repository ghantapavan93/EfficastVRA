"""Identity & Access Management — the auth seam + an explicit least-privilege permission model.

Identity is a **port** (`IdentityProvider`): the prototype ships `HeaderIdentityProvider` (the
`X-VRA-User` demo flow); a real deployment swaps in `OidcIdentityProvider` (validate a bearer JWT,
map claims → `Principal`) with no change to authorization. The **role on the resolved principal is
authoritative** — a client-claimed role is never trusted.

Authorization is an explicit **role → permission matrix** (least privilege). It is the documented,
testable counterpart of the role guards already enforced in the state machine + gateway. Crucially:
no role holds a machine-control permission (none exist), and the autonomous **agent service principal**
can propose/monitor but can never approve, release quality, or close — humans must.
"""

from __future__ import annotations

import abc
from typing import Optional

from sqlmodel import Session, select

from app.auth import Principal
from app.domain.enums import Role
from app.domain.models import User


# ── identity provider port ────────────────────────────────────────────────────
class IdentityProvider(abc.ABC):
    @abc.abstractmethod
    def authenticate(self, *, credential: Optional[str], session: Session) -> Principal: ...


class HeaderIdentityProvider(IdentityProvider):
    """Demo: ``credential`` is the X-VRA-User header → a seeded User. Role comes from the User row."""

    def authenticate(self, *, credential: Optional[str], session: Session) -> Principal:
        from fastapi import HTTPException

        from app.config import get_settings

        username = credential
        if not username:
            if not get_settings().demo_mode:
                raise HTTPException(status_code=401, detail="authentication required: set X-VRA-User")
            username = "s.vega"  # demo-only default principal
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None or not user.active:
            raise HTTPException(status_code=401, detail=f"unknown or inactive user '{username}'")
        return Principal(user_id=user.id, username=user.username, role=user.role,
                         plant_id=user.plant_id, tenant_id=user.tenant_id)


# A real adapter (documented shape, not wired):
#   class OidcIdentityProvider(IdentityProvider):
#       def authenticate(self, *, credential, session):
#           claims = verify_jwt(credential, jwks=self.jwks, audience=self.audience)  # signature + exp
#           role = map_group_to_role(claims["groups"])      # IdP groups → our Role
#           return Principal(user_id=claims["sub"], username=claims["preferred_username"],
#                            role=role, plant_id=claims["plant"], tenant_id=claims["tenant"])

DEFAULT_IDENTITY_PROVIDER: IdentityProvider = HeaderIdentityProvider()


# ── permission model (least privilege) ────────────────────────────────────────
PERMISSIONS: dict[Role, set[str]] = {
    Role.SUPERVISOR: {
        "review_recovery_contract", "approve_contingency", "accept_diagnosis",
        "record_supervisor_approval", "escalate_incident", "view_audit", "view_governance",
    },
    Role.TECHNICIAN: {
        "submit_measurement", "complete_intervention_evidence", "report_unexpected_condition",
        "view_assigned_evidence",
    },
    Role.QUALITY_ENGINEER: {
        "submit_quality_result", "approve_quality_release", "review_affected_lots", "view_quality",
        "review_knowledge",
    },
    Role.PLANT_ADMIN: {
        "review_recovery_contract", "approve_contingency", "accept_diagnosis", "escalate_incident",
        "pause_agent_side_effects", "view_system_health", "inspect_policy", "view_audit",
        "view_governance", "review_knowledge",
    },
    # The autonomous agent is a *service principal*: it proposes and observes, never decides closure.
    Role.AGENT: {
        "propose_recovery_contract", "request_missing_evidence", "monitor_recovery_cycles",
        "publish_recovery_decision", "create_knowledge_candidate", "reopen_incident",
    },
    Role.SYSTEM: {"apply_internal_transition"},
}

# Capabilities NO principal may ever hold — there is no permission, port, route, tool, or function
# for any of these (also enforced by the architecture fitness functions).
PROHIBITED_PERMISSIONS: set[str] = {
    "machine_start", "machine_stop", "machine_restart", "plc_modification", "setpoint_modification",
    "alarm_bypass", "interlock_bypass", "loto_confirmation", "automatic_quality_release",
    "model_controlled_closure",
}


def permissions_for(role: Role) -> list[str]:
    return sorted(PERMISSIONS.get(role, set()))


def can(role: Role, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())
