"""Deploy config (Render + Vercel + Neon): the managed-Postgres URL is normalized to the psycopg3
driver, and SQLite is left untouched so local dev/tests are unaffected. See docs/DEPLOYMENT.md."""

from __future__ import annotations

from app.db import _normalize_db_url


def test_postgres_urls_get_the_psycopg_driver():
    assert _normalize_db_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert (
        _normalize_db_url("postgresql://u:p@ep-x.us-east-2.aws.neon.tech/neondb?sslmode=require")
        == "postgresql+psycopg://u:p@ep-x.us-east-2.aws.neon.tech/neondb?sslmode=require"
    )
    # already-qualified driver is left alone (idempotent)
    assert _normalize_db_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"


def test_sqlite_url_is_unchanged():
    assert _normalize_db_url("sqlite:///x.db") == "sqlite:///x.db"
    assert _normalize_db_url("sqlite://") == "sqlite://"
