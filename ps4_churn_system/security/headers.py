"""
PS4 - Security Headers Middleware
Applies OWASP-recommended HTTP security headers to every response.
Prevents XSS, clickjacking, MIME sniffing, and information leakage.
"""

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import time


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to every HTTP response.
    Based on OWASP Secure Headers Project recommendations.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response: Response = await call_next(request)

        # ── Anti-Clickjacking ─────────────────────────────────────────────────
        response.headers["X-Frame-Options"] = "DENY"

        # ── XSS Protection ───────────────────────────────────────────────────
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # ── Prevent MIME Sniffing ────────────────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"

        # ── Referrer Policy ──────────────────────────────────────────────────
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ── Content Security Policy ───────────────────────────────────────────
        # Allows our CDN for Chart.js and Google Fonts — blocks everything else
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https://img.shields.io; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # ── Permissions Policy (disable dangerous browser APIs) ──────────────
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=()"
        )

        # ── HSTS (only in production / HTTPS) ────────────────────────────────
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # ── Remove server identification headers ─────────────────────────────
        if "server" in response.headers:
            del response.headers["server"]
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]

        # ── Timing header (for debugging / monitoring, not a secret) ─────────
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        # ── Cache control for API responses ──────────────────────────────────
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response


class InputSanitizer:
    """
    Utility class to sanitise and validate incoming data.
    Prevents injection attacks.
    """

    # Characters that must never appear in IDs or query params
    DANGEROUS_CHARS = ["<", ">", '"', "'", ";", "--", "/*", "*/",
                       "DROP", "SELECT", "INSERT", "DELETE", "UPDATE",
                       "EXEC", "UNION", "SCRIPT", "JAVASCRIPT"]

    @classmethod
    def sanitize_id(cls, value: str, max_len: int = 20) -> str:
        """Sanitise a customer/complaint ID. Allow only alphanumeric + underscore."""
        import re
        if not value:
            raise ValueError("ID cannot be empty")
        cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "", str(value))[:max_len]
        if not cleaned:
            raise ValueError(f"Invalid ID format: {value!r}")
        return cleaned

    @classmethod
    def sanitize_string(cls, value: str, max_len: int = 500) -> str:
        """Sanitise a free-text string. Strip dangerous patterns."""
        if not value:
            return ""
        value = str(value)[:max_len]
        for dangerous in cls.DANGEROUS_CHARS:
            value = value.replace(dangerous, "")
        return value.strip()

    @classmethod
    def validate_query_params(cls, params: dict) -> dict:
        """Validate and sanitise query parameters."""
        safe = {}
        allowed_tiers  = {"Critical", "High", "Medium", "Low", ""}
        allowed_queues = {"Active Outreach", "Watchlist", "Healthy", ""}

        for k, v in params.items():
            if k == "tier"  and v not in allowed_tiers:
                raise ValueError(f"Invalid tier value: {v!r}")
            if k == "queue" and v not in allowed_queues:
                raise ValueError(f"Invalid queue value: {v!r}")
            if k == "limit":
                v = max(1, min(200, int(v)))
            safe[k] = v
        return safe
