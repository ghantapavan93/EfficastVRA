"""Edge HTTP security middleware: hardening response headers, a request-body size guard, and
per-identity rate limiting.

This is defense-in-depth at the network edge; it complements (never replaces) the Agent Action
Gateway, which remains the single authorization choke point for every side effect. Oversized bodies
get 413, flooding gets 429 (with ``Retry-After``); both emit a structured security event. Security
headers are applied to every response, including the short-circuited ones.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app import security_events
from app.config import get_settings
from app.rate_limit import RateLimiter

_settings = get_settings()

# Module singleton so the live posture + tests can read/adjust it.
LIMITER = RateLimiter(limit=_settings.rate_limit_requests, window_s=_settings.rate_limit_window_s)

# Liveness/readiness + API docs are exempt from rate limiting (monitoring must never be throttled).
_EXEMPT_PREFIXES = ("/health", "/healthz", "/api/health", "/docs", "/redoc", "/openapi")
_DOCS_PREFIXES = ("/docs", "/redoc", "/openapi")

# Static security headers safe for a JSON API. CSP/HSTS are applied conditionally below.
SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
    "X-Permitted-Cross-Domain-Policies": "none",
}
# An API serves only JSON — nothing should load resources or frame it. Locked all the way down.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"


def _source_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _identity_key(request: Request) -> str:
    user = request.headers.get("X-VRA-User")
    if user:
        return f"user:{user}"
    return f"ip:{_source_ip(request) or 'anon'}"


def apply_security_headers(response: Response, path: str) -> None:
    if not _settings.security_headers_enabled:
        return
    is_docs = path.startswith(_DOCS_PREFIXES)
    for key, value in SECURITY_HEADERS.items():
        if is_docs and key == "X-Frame-Options":
            continue  # Swagger/Redoc render their own UI; don't fight their framing
        response.headers.setdefault(key, value)
    if not is_docs:
        response.headers.setdefault("Content-Security-Policy", API_CSP)
    if _settings.security_hsts_enabled:
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
    if path.startswith("/api"):
        response.headers.setdefault("Cache-Control", "no-store")


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        cid = request.headers.get("X-Correlation-Id", "")

        # 1) request-body size guard (Content-Length pre-check, before any handler runs)
        content_length = request.headers.get("content-length")
        if (content_length and _settings.max_request_body_bytes
                and content_length.isdigit() and int(content_length) > _settings.max_request_body_bytes):
            security_events.emit(
                "oversized_request", "warning", route=path, source_ip=_source_ip(request),
                correlation_id=cid, reason=f"content-length {content_length} > {_settings.max_request_body_bytes}",
            )
            resp = JSONResponse(status_code=413, content={"detail": "request body too large", "code": "body_too_large"})
            apply_security_headers(resp, path)
            return resp

        # 2) per-identity rate limiting (skip exempt monitoring/docs paths)
        if _settings.rate_limit_enabled and not path.startswith(_EXEMPT_PREFIXES):
            decision = LIMITER.check(_identity_key(request))
            if not decision.allowed:
                security_events.emit_denial(
                    stage="rate_limit", reason="rate limit exceeded", route=path,
                    source_ip=_source_ip(request), correlation_id=cid,
                )
                resp = JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded", "code": "rate_limited",
                             "retry_after": decision.retry_after},
                )
                resp.headers["Retry-After"] = str(decision.retry_after)
                resp.headers["X-RateLimit-Limit"] = str(decision.limit)
                resp.headers["X-RateLimit-Remaining"] = str(decision.remaining)
                apply_security_headers(resp, path)
                return resp

        response = await call_next(request)
        apply_security_headers(response, path)
        return response
