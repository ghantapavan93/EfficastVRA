"""Revision- and approval-aware retrieval over a small synthetic manufacturing corpus.

Retrieval filters by **applicability + approval status before semantic similarity** so an obsolete
revision or an unapproved note can never outrank current approved policy. A prompt-injection document
is included to prove retrieved text cannot change tool permissions.
"""

from app.rag.retrieval import RetrievedChunk, detect_conflicts, search

__all__ = ["search", "detect_conflicts", "RetrievedChunk"]
