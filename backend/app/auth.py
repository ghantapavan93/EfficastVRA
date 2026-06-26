"""Local identity (no external IdP).

A request carries ``X-VRA-User: <username>`` identifying a seeded :class:`User`. The role on that
user is authoritative for authorization — the backend never trusts a role claimed by the client. For
demo convenience an absent header resolves to the supervisor principal **in demo mode only**; in any
other environment a missing credential is unauthenticated (401), never silently elevated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.domain.enums import Role
from app.domain.models import User


@dataclass
class Principal:
    user_id: str
    username: str
    role: Role
    plant_id: str
    tenant_id: str
    is_human: bool = True


def get_principal(
    x_vra_user: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
) -> Principal:
    username = x_vra_user
    if not username:
        # An absent credential is a convenience ONLY in demo mode. Anywhere else, "no identity" must be
        # unauthenticated — never auto-elevated to the supervisor principal (the system's own thesis:
        # don't trust an unproven green light).
        if not get_settings().demo_mode:
            raise HTTPException(status_code=401, detail="authentication required: set X-VRA-User")
        username = "s.vega"  # demo-only default principal (supervisor)
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail=f"unknown or inactive user '{username}'")
    return Principal(
        user_id=user.id, username=user.username, role=user.role,
        plant_id=user.plant_id, tenant_id=user.tenant_id,
    )


def agent_principal(plant_id: str, tenant_id: str) -> Principal:
    """The autonomous agent's own principal (cannot satisfy human-approval requirements)."""
    return Principal(
        user_id="AGENT", username="recovery-agent", role=Role.AGENT,
        plant_id=plant_id, tenant_id=tenant_id, is_human=False,
    )
