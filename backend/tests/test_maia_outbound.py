"""MAIA outbound contract — structured messages, deep-links only (never tool execution), 7 kinds."""

from __future__ import annotations

import pytest

from app.domain.models import Incident
from app.integration.efficast.maia import (
    MAIA_KINDS,
    MaiaAction,
    build_maia_message,
    maia_messages_for,
)
from app.seed.northstar import IDS
from app.workflow.demo import run_scenario


def test_all_seven_kinds_build_valid_messages():
    assert len(MAIA_KINDS) == 7
    for kind in MAIA_KINDS:
        m = build_maia_message(kind, "INC-2841")
        assert m.kind == kind and m.title and m.body and m.surface == "whatsapp"
        assert all(a.deep_link.startswith("/missions/") for a in m.actions)


def test_message_actions_carry_no_tool_execution():
    # an action is a deep-link only — the contract has no field that could execute a tool / free-form command
    fields = set(MaiaAction.model_fields)
    assert fields == {"label", "deep_link"}
    assert "tool" not in fields and "command" not in fields


def test_unknown_kind_raises():
    with pytest.raises(ValueError):
        build_maia_message("not_a_kind", "INC-2841")


def test_derive_message_for_verified_incident(session):
    run_scenario(session, log=lambda *a: None)
    inc = session.get(Incident, IDS["incident"])
    msgs = maia_messages_for(session, inc)
    assert len(msgs) == 1 and msgs[0].kind == "recovery_verified"
