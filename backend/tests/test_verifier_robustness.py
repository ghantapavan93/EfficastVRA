"""Verifier-robustness tests (Phase 29) — close the deep-critique holes in the core thesis.

H-A: a stable cycle must be genuinely fault-free, not merely free of the one originating fault.
C1:  a contract for an incident with a known fault MUST verify that fault's non-recurrence, or the
     deterministic verification is vacuous — the builder refuses such a contract.
"""

from __future__ import annotations

import pytest

from app.domain.contract import ConditionSpec, RecoveryContractSpec
from app.domain.enums import CompareOp, ConditionKind
from app.domain.models import Incident, RecoveryCondition, RecoveryObservation
from app.seed.northstar import IDS
from app.services.evaluator import is_stable_observation
from app.workflow.contract_builder import persist_contract


def test_any_fault_breaks_the_stable_streak():
    # The contract only names F27, but a DIFFERENT, secondary fault during the window with otherwise
    # nominal metrics must still make the cycle non-stable (a new failure is not "30 stable cycles").
    conds = [RecoveryCondition(contract_id="c", incident_id="i", kind=ConditionKind.MACHINE,
                               key="fault_f27", op=CompareOp.NOT_RECUR, fault_code="F27")]
    foreign_fault = RecoveryObservation(incident_id="i", contract_id="c", window_id="w",
                                        cycle_index=5, fault_code="F99", vibration=3.0)
    assert is_stable_observation(foreign_fault, conds) is False
    clean = RecoveryObservation(incident_id="i", contract_id="c", window_id="w",
                                cycle_index=5, fault_code=None, vibration=3.0)
    assert is_stable_observation(clean, conds) is True


def _spec(fault_code: str) -> RecoveryContractSpec:
    return RecoveryContractSpec(
        contract_no="RC-TEST", incident_id=IDS["incident"], objective="verify",
        machine_conditions=[ConditionSpec(key="fault_x", kind=ConditionKind.MACHINE,
                                          label="fault must not recur", op=CompareOp.NOT_RECUR,
                                          fault_code=fault_code)],
    )


def test_contract_must_test_the_originating_fault(session):
    inc = session.get(Incident, IDS["incident"])  # seed fault_code == "F27"
    assert inc.fault_code == "F27"
    # A contract whose NOT_RECUR points at the WRONG fault is refused by the deterministic builder —
    # it could not detect the relapse it purports to verify.
    with pytest.raises(ValueError, match="non-recurrence of the originating fault"):
        persist_contract(session, inc, _spec("WRONG-FAULT"))


def test_correctly_bound_contract_persists(session):
    inc = session.get(Incident, IDS["incident"])
    contract = persist_contract(session, inc, _spec(inc.fault_code))  # binds NOT_RECUR to F27
    assert contract.id and inc.current_contract_id == contract.id
