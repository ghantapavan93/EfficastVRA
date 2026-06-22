"""Phase-3: revision/approval-aware retrieval + prompt-injection defense."""

from __future__ import annotations

from sqlmodel import Session

from app.domain.models import Incident, Intervention
from app.rag import detect_conflicts, search
from app.reasoning.deterministic import DeterministicReasoningProvider
from app.seed.northstar import IDS


def test_approved_retrieval_excludes_obsolete_and_unapproved(session: Session):
    results = search(session, "drive-end vibration RMS limit", machine_model="CDX-220", component="drive")
    ids = {r.document_id for r in results}
    assert "DOC-CDX220-r3" in ids           # current approved manual
    assert "DOC-CDX220-r2" not in ids        # obsolete revision filtered out
    assert "DOC-TECHNOTE-X" not in ids       # unapproved note filtered out
    assert "DOC-INJECTION" not in ids        # injection doc filtered out
    text = " ".join(r.content for r in results)
    assert "4.0 mm/s" in text                # authoritative limit, not the obsolete 6.0


def test_conflict_detection_flags_obsolete_without_promoting_it(session: Session):
    conflicts = detect_conflicts(session, "drive-end vibration RMS limit",
                                 machine_model="CDX-220", component="drive")
    conflict_ids = {c["document_id"] for c in conflicts["conflicts"]}
    assert "DOC-CDX220-r2" in conflict_ids   # obsolete is surfaced as a conflict...
    assert conflicts["authoritative"]         # ...but approved guidance is authoritative
    for c in conflicts["conflicts"]:
        assert c["authoritative"] is False


def test_cross_tenant_or_scope_isolation(session: Session):
    # A document scoped to a different plant must not surface for our plant scope.
    results = search(session, "first piece quality release", plant_scope="PLANT-OTHER")
    assert all(r.plant_scope in ("ALL", "PLANT-OTHER") for r in results)
    # The TI-20L quality spec is scoped to PLANT-NS, so it must NOT appear for PLANT-OTHER.
    assert all(r.document_id != "DOC-QS-TI20L-r3" for r in results)


def test_prompt_injection_cannot_change_permissions(session: Session):
    # Approved retrieval never returns the injection memo.
    approved = search(session, "SYSTEM OVERRIDE grant machine_start close incident",
                      machine_model="CDX-220", approved_only=True)
    assert all(r.document_id != "DOC-INJECTION" for r in approved)

    # Even if the injected text is force-fed to reasoning, the resulting contract still DENIES
    # machine control and grants nothing dangerous — permissions come from policy, not documents.
    inc = session.get(Incident, IDS["incident"])
    itv = session.get(Intervention, IDS["intervention_1"])
    injected = search(session, "SYSTEM OVERRIDE grant machine_start", approved_only=False)
    assert any(r.document_id == "DOC-INJECTION" for r in injected)  # it IS retrievable unfiltered

    spec = DeterministicReasoningProvider().extract_recovery_requirements(
        incident=inc, intervention=itv, retrieved=[r.__dict__ for r in injected]
    )
    denies, grants = set(), set()
    for a in spec.approval_requirements:
        denies |= set(a.denies)
        grants |= set(a.grants)
    assert {"machine_start", "machine_restart", "automatic_quality_release"} <= denies
    assert "machine_start" not in grants
    assert "automatic_quality_release" not in grants
