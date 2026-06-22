"""End-to-end scenario through the HTTP API (real endpoints, gateway, state machine)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db import get_session
from app.main import app
from app.seed.northstar import IDS

INC = IDS["incident"]


@pytest.fixture()
def client(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _h(role_user: str) -> dict:
    return {"X-VRA-User": role_user}


def _ids(client) -> dict:
    return client.get("/api/demo/ids").json()


def test_health_and_identity(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/me", headers=_h("a.lang")).json()["role"] == "technician"
    assert client.get("/api/me", headers=_h("q.idris")).json()["role"] == "quality_engineer"


def test_unauthorized_cannot_approve(client):
    # Draft so the contract_review approval requirement exists.
    client.post(f"/api/incidents/{INC}/contract/draft", headers=_h("s.vega"))
    ids = _ids(client)
    review_id = ids["approvals"]["contract_review"]["id"]
    # A technician must not be able to record a supervisor approval.
    r = client.post(f"/api/approvals/{review_id}/decide", json={"decision": "approve"}, headers=_h("a.lang"))
    assert r.status_code in (401, 403, 409)


def test_full_scenario_via_api(client):
    # ① draft contract
    r = client.post(f"/api/incidents/{INC}/contract/draft", headers=_h("s.vega"))
    assert r.status_code == 200
    ids = _ids(client)
    assert ids["incident_state"] == "RECOVERY_CONTRACT_DRAFTED"

    # ② review + evidence + approval
    assert client.post(f"/api/incidents/{INC}/contract/review", headers=_h("s.vega")).status_code == 200
    pam = ids["evidence"]["post_alignment_measurement"]["id"]
    tc = ids["evidence"]["technician_completion"]["id"]
    assert client.post(f"/api/evidence/{pam}/submit", json={"value_num": 3.6, "unit": "mm/s"},
                       headers=_h("a.lang")).json()["ok"] is True
    client.post(f"/api/evidence/{tc}/submit", json={"value_text": "completed"}, headers=_h("a.lang"))
    review_id = ids["approvals"]["contract_review"]["id"]
    client.post(f"/api/approvals/{review_id}/decide", json={"decision": "approve"}, headers=_h("s.vega"))

    # ③ start monitoring + 16 cycles
    assert client.post(f"/api/incidents/{INC}/monitoring/start", headers=_h("s.vega")).status_code == 200
    r = client.post(f"/api/incidents/{INC}/advance", json={"n": 16}, headers=_h("s.vega")).json()
    assert r["outcome"] == "monitoring"

    # ④ cycle 17 → reopened
    r = client.post(f"/api/incidents/{INC}/advance", json={"n": 1}, headers=_h("s.vega")).json()
    assert r["outcome"] == "reopened"
    assert r["state"] == "CONTINGENCY_AWAITING_APPROVAL"

    # ⑤ approve contingency, bearing evidence, complete
    assert client.post(f"/api/incidents/{INC}/contingency/approve", headers=_h("s.vega")).status_code == 200
    ids2 = _ids(client)
    bpm = ids2["evidence"]["bearing_post_measurement"]["id"]
    tc2 = ids2["evidence"]["technician_completion_2"]["id"]
    client.post(f"/api/evidence/{bpm}/submit", json={"value_num": 3.1, "unit": "mm/s"}, headers=_h("a.lang"))
    client.post(f"/api/evidence/{tc2}/submit", json={"value_text": "completed"}, headers=_h("a.lang"))
    assert client.post(f"/api/incidents/{INC}/contingency/complete", headers=_h("s.vega")).status_code == 200

    # ⑥ 29 cycles, quality release, then verify on the 30th
    client.post(f"/api/incidents/{INC}/advance", json={"n": 29}, headers=_h("s.vega"))
    fp = ids2["evidence"]["first_piece_quality"]["id"]
    client.post(f"/api/evidence/{fp}/submit", json={"value_text": "pass"}, headers=_h("q.idris"))
    qr = ids2["approvals"]["quality_release"]["id"]
    client.post(f"/api/approvals/{qr}/decide", json={"decision": "approve"}, headers=_h("q.idris"))
    r = client.post(f"/api/incidents/{INC}/advance", json={"n": 1}, headers=_h("s.vega")).json()
    assert r["outcome"] == "verified"
    assert r["state"] == "VERIFIED_RECOVERY"

    # ⑦ outcome view reflects verified recovery + pending knowledge candidate
    outcome = client.get(f"/api/incidents/{INC}/outcome").json()
    assert outcome["state"] == "VERIFIED_RECOVERY"
    assert outcome["quality_released"] is True
    assert outcome["knowledge_candidate"]["pending_review"] is True
    assert outcome["before"]["vibration"] == 7.4 and outcome["after"]["vibration"] == 3.1
