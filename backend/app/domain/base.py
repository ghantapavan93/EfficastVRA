"""Base model mixins + ID/time helpers.

Timestamps are **naive UTC** throughout (``datetime.now(UTC).replace(tzinfo=None)``) so that SQLite
round-trips and freshness math never mix aware/naive values. Production on Postgres keeps the same
convention for portability.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Naive UTC 'now' — the single source of time for the whole backend."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def id_factory(prefix: str):
    """Return a zero-arg callable producing a prefixed, sortable-ish unique id."""

    def factory() -> str:
        return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"

    return factory


class Base(SQLModel):
    """Common columns. Subclasses set ``table=True`` and their own prefixed ``id``."""

    created_at: datetime = Field(default_factory=utcnow, index=True)
    updated_at: datetime = Field(
        default_factory=utcnow, sa_column_kwargs={"onupdate": utcnow}
    )
    version: int = Field(default=1, description="Optimistic-lock / row version")
