"""Defense-in-depth security tests: edge hardening (headers, rate limiting, body guard), keyed audit
signing + tamper detection, classified security-event emission, and the live /api/security posture.
"""

from __future__ import annotations

import dataclasses

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import security_http
from app.db import get_session
from app.domain.enums import AuditEventType, Role
from app.domain.models import AuditEvent
from app.main import app
from tests.helpers import principal


@pytest.fixture()
def client(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _h(user: str) -> dict:
    return {"X-VRA-User": user}


# ── edge hardening: response headers ───────────────────────────────────────────────────────────
def test_security_headers_present_on_api(client):
    r = client.get("/api/me", headers=_h("s.vega"))
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"
    assert "default-src 'none'" in r.headers.get("Content-Security-Policy", "")
    assert r.headers.get("Cross-Origin-Opener-Policy") == "same-origin"
    assert r.headers.get("Cache-Control") == "no-store"  # API responses are never cached


def test_health_is_exempt_but_still_hardened(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"  # headers apply everywhere


# ── edge hardening: request body-size guard ────────────────────────────────────────────────────
def test_oversized_body_rejected_with_413(client, monkeypatch):
    small = dataclasses.replace(security_http._settings, max_request_body_bytes=200)
    monkeypatch.setattr(security_http, "_settings", small)
    r = client.post("/api/me", content="A" * 500)  # guard fires before routing
    assert r.status_code == 413
    assert r.json()["code"] == "body_too_large"


# ── edge hardening: per-identity rate limiting ─────────────────────────────────────────────────
def test_rate_limit_returns_429_with_retry_after(client, monkeypatch):
    monkeypatch.setattr(security_http.LIMITER, "limit", 3)
    security_http.LIMITER.reset()
    codes = [client.get("/api/me", headers=_h("s.vega")).status_code for _ in range(5)]
    assert codes.count(200) <= 3
    assert 429 in codes
    blocked = client.get("/api/me", headers=_h("s.vega"))
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 0
    assert "X-RateLimit-Limit" in blocked.headers


def test_rate_limit_is_per_identity(client, monkeypatch):
    monkeypatch.setattr(security_http.LIMITER, "limit", 2)
    security_http.LIMITER.reset()
    for _ in range(3):
        client.get("/api/me", headers=_h("s.vega"))  # exhaust s.vega
    # a different identity is unaffected — quotas are per principal
    assert client.get("/api/me", headers=_h("a.lang")).status_code == 200


# ── keyed audit signing + tamper detection ─────────────────────────────────────────────────────
def test_audit_hmac_signs_and_detects_signature_forgery(session, monkeypatch):
    from app.workflow import audit

    monkeypatch.setattr(audit, "current_hmac_key", lambda: "test-secret-key")
    cid = "cid-hmac"
    for i in range(3):
        audit.record_audit(session, type=AuditEventType.ACTION_PROPOSED, correlation_id=cid,
                           actor="s.vega", role=Role.SUPERVISOR, summary=f"event {i}")
    ok = audit.verify_audit_chain(session, cid)
    assert ok["ok"] and ok["signed"] and ok["authenticated"] and ok["count"] == 3

    # Forge: rewrite a row's signature only. The public hash chain still links, but HMAC won't verify.
    rows = session.exec(
        select(AuditEvent).where(AuditEvent.correlation_id == cid).order_by(AuditEvent.seq)  # type: ignore[arg-type]
    ).all()
    rows[1].entry_hmac = "00" * 32
    session.add(rows[1])
    session.flush()
    forged = audit.verify_audit_chain(session, cid)
    assert forged["ok"] is False
    assert forged["authenticated"] is False
    assert forged.get("signature_broken") is True


def test_audit_hash_chain_detects_content_tamper(session, monkeypatch):
    from app.workflow import audit

    monkeypatch.setattr(audit, "current_hmac_key", lambda: "test-secret-key")
    cid = "cid-tamper"
    for i in range(3):
        audit.record_audit(session, type=AuditEventType.ACTION_PROPOSED, correlation_id=cid,
                           actor="s.vega", role=Role.SUPERVISOR, summary=f"event {i}")
    rows = session.exec(
        select(AuditEvent).where(AuditEvent.correlation_id == cid).order_by(AuditEvent.seq)  # type: ignore[arg-type]
    ).all()
    rows[1].summary = "tampered narrative"  # entry_hash no longer matches content
    session.add(rows[1])
    session.flush()
    res = audit.verify_audit_chain(session, cid)
    assert res["ok"] is False
    assert res["broken_at_seq"] == rows[1].seq


def test_audit_unsigned_when_no_key(session, monkeypatch):
    from app.workflow import audit

    monkeypatch.setattr(audit, "current_hmac_key", lambda: "")
    cid = "cid-nokey"
    audit.record_audit(session, type=AuditEventType.STATE_TRANSITION, correlation_id=cid,
                       actor="x", role=Role.SYSTEM, summary="s")
    res = audit.verify_audit_chain(session, cid)
    assert res["ok"] is True
    assert res["signed"] is False
    assert res["authenticated"] is None  # not applicable when signing is off (honest)


# ── classified security-event emission on gateway denial ───────────────────────────────────────
def test_prohibited_action_denied_emits_critical_event(session):
    from app import security_events
    from app.gateway import gateway

    sup = principal(session, "s.vega")
    with pytest.raises(gateway.GatewayError) as ei:
        gateway.execute(session, tool_name="machine_start", raw_args={}, principal=sup,
                        correlation_id="cid-prohibited", incident_id=None)
    assert ei.value.status_code == 403
    counts = security_events.REGISTRY.counts()
    assert counts.get("prohibited_action_attempt", 0) >= 1
    assert security_events.REGISTRY.critical_count() >= 1


# ── live security posture endpoint ─────────────────────────────────────────────────────────────
def test_security_posture_endpoint_shape(client):
    p = client.get("/api/security", headers=_h("s.vega")).json()
    for key in ("headers", "rate_limiting", "request_guard", "audit_signing", "gateway",
                "detection", "control_alignment", "control_checks", "honest_gaps", "versions"):
        assert key in p, f"missing posture section: {key}"
    assert p["rate_limiting"]["enabled"] is True
    assert "machine_start" in p["gateway"]["prohibited_actions"]
    assert all("status" in c for c in p["control_checks"])
    assert {"OWASP", "NIST", "ISO/IEC", "IEC"} <= {c["framework"].split(" ")[0] for c in p["control_alignment"]}
    assert len(p["honest_gaps"]) >= 1  # honesty: gaps disclosed, not hidden


def test_governance_gaps_reconciled_with_new_controls(session):
    from app.services.governance import posture

    p = posture(session)
    # The old "No API rate limiting" gap is now implemented, so it must no longer be claimed.
    assert not any(g == "No API rate limiting / quota." for g in p["honest_gaps"])
    assert "edge_hardening" in p["security"]
    assert p["security"]["posture_detail"] == "/api/security"
