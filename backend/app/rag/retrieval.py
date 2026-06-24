"""Filtered semantic retrieval.

Order of operations is the whole point: **filter by applicability + approval status first**, then
rank by cosine similarity. An obsolete revision or unapproved note is removed *before* ranking, so it
can never become authoritative — no matter how lexically similar it is to the query.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, select

from app.domain.enums import DocApprovalStatus
from app.domain.models import DocumentChunk
from app.rag.embeddings import cosine, embed


@dataclass
class RetrievedChunk:
    document_id: str
    doc_type: str
    revision: str
    machine_model: str
    component: str
    approval_status: str
    plant_scope: str
    page: int
    section: str
    content: str
    content_hash: str
    score: float
    superseded_by: Optional[str] = None


def _applicable(chunk: DocumentChunk, machine_model: Optional[str], component: Optional[str],
                plant_scope: Optional[str]) -> bool:
    if machine_model and chunk.machine_model not in ("", "ALL", machine_model):
        return False
    if component and chunk.component not in ("", "ALL", component):
        return False
    if plant_scope and chunk.plant_scope not in ("ALL", plant_scope):
        return False
    return True


def _to_view(chunk: DocumentChunk, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=chunk.document_id, doc_type=chunk.doc_type.value, revision=chunk.revision,
        machine_model=chunk.machine_model, component=chunk.component,
        approval_status=chunk.approval_status.value, plant_scope=chunk.plant_scope,
        page=chunk.page, section=chunk.section, content=chunk.content,
        content_hash=chunk.content_hash, score=round(score, 4), superseded_by=chunk.superseded_by,
    )


def search(
    session: Session,
    query: str,
    *,
    machine_model: Optional[str] = None,
    component: Optional[str] = None,
    plant_scope: Optional[str] = None,
    approved_only: bool = True,
    k: int = 5,
) -> list[RetrievedChunk]:
    chunks = session.exec(select(DocumentChunk)).all()
    qv = embed(query)

    filtered: list[DocumentChunk] = []
    for c in chunks:
        if approved_only and (c.approval_status != DocApprovalStatus.APPROVED or c.superseded_by):
            continue  # approval/recency filter BEFORE similarity
        if not _applicable(c, machine_model, component, plant_scope):
            continue
        filtered.append(c)

    scored = [(c, cosine(qv, c.embedding)) for c in filtered]
    scored.sort(key=lambda t: t[1], reverse=True)
    return [_to_view(c, s) for c, s in scored[:k]]


def detect_conflicts(
    session: Session,
    query: str,
    *,
    machine_model: Optional[str] = None,
    component: Optional[str] = None,
    plant_scope: Optional[str] = None,
    k: int = 4,
) -> dict:
    """Return authoritative (approved) guidance + any obsolete/unapproved chunks that matched the
    same query, each flagged with *why* it is not authoritative."""
    authoritative = search(session, query, machine_model=machine_model, component=component,
                           plant_scope=plant_scope, approved_only=True, k=k)
    everything = search(session, query, machine_model=machine_model, component=component,
                        plant_scope=plant_scope, approved_only=False, k=k * 3)

    conflicts: list[dict] = []
    # Key on (document, revision, section) — NOT content hash. An obsolete revision that repeats a
    # sentence verbatim from the approved chunk would share a content hash and be silently dropped,
    # hiding exactly the stale-guidance conflict this function exists to surface.
    auth_keys = {(c.document_id, c.revision, c.section) for c in authoritative}
    for c in everything:
        if (c.document_id, c.revision, c.section) in auth_keys:
            continue
        if c.approval_status != DocApprovalStatus.APPROVED.value or c.superseded_by:
            reason = (
                "superseded by " + c.superseded_by if c.superseded_by
                else f"approval status is {c.approval_status}"
            )
            conflicts.append({
                "document_id": c.document_id, "revision": c.revision, "section": c.section,
                "approval_status": c.approval_status, "reason": reason,
                "excerpt": c.content[:160], "authoritative": False,
            })

    return {
        "authoritative": [c.__dict__ for c in authoritative],
        "conflicts": conflicts,
        "note": ("Conflicting non-authoritative documents are excluded from guidance; current "
                 "approved policy/manual prevails."),
    }
