"""Runtime configuration.

Deliberately dependency-free (plain ``os.environ`` + a frozen dataclass) so the backend has one
fewer thing that can break at install time. The whole system runs on defaults with no secrets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Anchor the default SQLite DB to the backend package dir so the CLI and uvicorn always share one
# file regardless of the current working directory they are launched from.
_DEFAULT_DB = (Path(__file__).resolve().parent.parent / "var" / "vra.db").as_posix()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Verified Recovery Agent"
    environment: str = os.getenv("VRA_ENV", "synthetic-demo")
    # VRA_DATABASE_URL is canonical; DATABASE_URL is accepted too (Render/Neon/Heroku convention).
    database_url: str = (
        os.getenv("VRA_DATABASE_URL") or os.getenv("DATABASE_URL") or f"sqlite:///{_DEFAULT_DB}"
    )
    tenant_id: str = os.getenv("VRA_TENANT", "northstar")
    plant_id: str = os.getenv("VRA_PLANT", "PLANT-NS")

    reasoning_provider: str = os.getenv("VRA_REASONING", "deterministic")
    reasoning_base_url: str = os.getenv("VRA_REASONING_BASE_URL", "")
    reasoning_api_key: str = os.getenv("VRA_REASONING_API_KEY", "")
    reasoning_model: str = os.getenv("VRA_REASONING_MODEL", "claude-opus-4-8")

    frontend_origin: str = os.getenv("VRA_FRONTEND_ORIGIN", "http://localhost:3000")
    policy_version: str = os.getenv("VRA_POLICY_VERSION", "policy-2026.06")
    workflow_version: str = os.getenv("VRA_WORKFLOW_VERSION", "wf-1")

    # ── Security hardening (defense-in-depth at the edge) ──────────────────────────────────────
    # Limits below are PROTOTYPE_ASSUMPTIONs (our deployment choices, not claims) — all env-tunable.
    security_headers_enabled: bool = os.getenv("VRA_SECURITY_HEADERS", "1") == "1"
    # HSTS only makes sense once TLS terminates here/upstream — off by default (honest).
    security_hsts_enabled: bool = os.getenv("VRA_SECURITY_HSTS", "0") == "1"
    rate_limit_enabled: bool = os.getenv("VRA_RATE_LIMIT", "1") == "1"
    rate_limit_requests: int = int(os.getenv("VRA_RATE_LIMIT_REQUESTS", "600"))  # per window, per identity
    rate_limit_window_s: int = int(os.getenv("VRA_RATE_LIMIT_WINDOW_S", "60"))
    max_request_body_bytes: int = int(os.getenv("VRA_MAX_BODY_BYTES", "1048576"))  # 1 MiB
    # Keyed audit signing. Empty ⇒ keyed signing OFF (the SHA-256 hash chain still runs). Set a strong
    # secret (from a vault/KMS in production) to make the audit trail unforgeable without the key.
    audit_hmac_key: str = os.getenv("VRA_AUDIT_HMAC_KEY", "")

    @property
    def demo_mode(self) -> bool:
        return os.getenv("VRA_DEMO_MODE", "1") == "1"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
