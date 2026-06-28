"""Sensor Trust Gate — TRUSTED / DEGRADED / UNTRUSTED / UNKNOWN, and the invariant that an untrusted or
unknown sensor can't satisfy a hard recovery condition (caps an otherwise-VERIFIED recovery to INSUFFICIENT)."""

from __future__ import annotations

from datetime import timedelta

from sqlmodel import select

from app.domain.base import utcnow
from app.domain.models import Incident, RecoveryObservation, RecoveryWindow
from app.seed.northstar import IDS
from app.services.disposition import assess_disposition
from app.services.sensor_trust import assess_sensor_trust, classify_sensor
from app.workflow.demo import run_scenario
from tests.helpers import to_quality_released


def test_classify_healthy_series_is_trusted():
    assert classify_sensor([3.0, 3.1, 3.05, 3.2, 3.0, 3.15, 3.1, 3.05], metric="vibration").status == "TRUSTED"


def test_classify_flatline_is_untrusted():
    assert classify_sensor([3.1] * 10, metric="vibration").status == "UNTRUSTED"


def test_classify_impossible_value_is_untrusted():
    assert classify_sensor([3.0, 3.1, 3.05, 3.2, 3.0, 3.15, 3.1, 999.0], metric="vibration").status == "UNTRUSTED"


def test_classify_few_samples_is_unknown():
    assert classify_sensor([3.1, 3.2], metric="vibration").status == "UNKNOWN"


def test_classify_calibration_overdue_is_degraded():
    r = classify_sensor([3.0, 3.1, 3.05, 3.2, 3.0, 3.15, 3.1, 3.05], metric="vibration",
                        calibration_due=utcnow() - timedelta(days=1))
    assert r.status == "DEGRADED" and any("calibration" in x for x in r.reasons)


def test_hero_sensors_are_trusted(session):
    run_scenario(session, log=lambda *a: None)
    inc = session.get(Incident, IDS["incident"])
    assert assess_sensor_trust(session, inc)["status"] == "TRUSTED"


def test_untrusted_sensor_blocks_verified_in_disposition(session):
    _svc, inc, c2 = to_quality_released(session, cycles=30)
    assert assess_disposition(session, inc)["disposition"] == "VERIFIED"   # baseline, sensors trusted
    win = session.exec(select(RecoveryWindow).where(RecoveryWindow.contract_id == c2.id)
                       .order_by(RecoveryWindow.sequence.desc())).first()
    for o in session.exec(select(RecoveryObservation).where(RecoveryObservation.window_id == win.id)).all():
        o.vibration = 3.1   # flatline the vibration sensor → stuck/untrusted
        session.add(o)
    session.commit()
    d = assess_disposition(session, inc)
    assert d["sensor_trust"]["status"] == "UNTRUSTED"
    assert d["disposition"] == "INSUFFICIENT_EVIDENCE" and d["can_close"] is False
