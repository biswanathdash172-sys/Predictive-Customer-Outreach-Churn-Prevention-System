"""
PS4 - Rate Limiter
Protects API endpoints from brute-force attacks, scraping, and abuse.
Uses in-memory sliding window counters per IP address.
"""

import time
import hashlib
import logging
from collections import defaultdict, deque
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("ps4.ratelimit")


class SlidingWindowRateLimiter:
    """
    Per-IP sliding window rate limiter.
    Tracks request timestamps in a deque and evicts expired ones.
    """

    def __init__(self):
        # ip_hash -> deque of timestamps
        self._windows: dict[str, deque] = defaultdict(deque)
        # ip_hash -> block_until timestamp
        self._blocked: dict[str, float] = {}

    def _hash_ip(self, ip: str) -> str:
        """Hash the IP so it's never stored in plaintext."""
        return hashlib.sha256(ip.encode()).hexdigest()[:16]

    def is_allowed(self, ip: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        """
        Check if this IP is within rate limit.
        Returns (allowed: bool, requests_remaining: int)
        """
        ip_hash = self._hash_ip(ip)
        now = time.time()

        # Check if IP is in hard-block period
        if ip_hash in self._blocked:
            if now < self._blocked[ip_hash]:
                return False, 0
            else:
                del self._blocked[ip_hash]

        window = self._windows[ip_hash]

        # Evict timestamps older than the window
        cutoff = now - window_seconds
        while window and window[0] < cutoff:
            window.popleft()

        # Check limit
        if len(window) >= limit:
            # Too many requests — apply a short block
            self._blocked[ip_hash] = now + 30  # block for 30s
            logger.warning(f"Rate limit exceeded for IP hash {ip_hash}")
            return False, 0

        # Record this request
        window.append(now)
        return True, limit - len(window)

    def get_stats(self) -> dict:
        return {
            "tracked_ips":  len(self._windows),
            "blocked_ips":  len(self._blocked),
        }


# Module-level limiter instances
general_limiter = SlidingWindowRateLimiter()
ai_limiter      = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract real client IP, checking X-Forwarded-For for proxied requests."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (leftmost = original client)
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting middleware.
    - General API: configurable requests/minute per IP
    - AI endpoints: stricter limit (Claude API is expensive)
    - Static assets: no limit
    """

    def __init__(self, app, general_limit: int = 60, ai_limit: int = 10):
        super().__init__(app)
        self.general_limit = general_limit
        self.ai_limit      = ai_limit

        # AI-heavy endpoints that need stricter limits
        self.ai_endpoints = {
            "/api/generate-message",
            "/api/rm-briefing",
            "/api/complaints/analyse",
            "/api/run-campaign",
        }

    def _is_ai_endpoint(self, path: str) -> bool:
        return any(path.startswith(ep) for ep in self.ai_endpoints)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip rate limiting for static assets and health check
        if path.startswith("/static") or path == "/health":
            return await call_next(request)

        ip = get_client_ip(request)

        # Apply stricter limit for AI endpoints
        if self._is_ai_endpoint(path):
            allowed, remaining = ai_limiter.is_allowed(ip, self.ai_limit, window_seconds=60)
            limit_used = self.ai_limit
        else:
            allowed, remaining = general_limiter.is_allowed(ip, self.general_limit, window_seconds=60)
            limit_used = self.general_limit

        if not allowed:
            logger.warning(f"Rate limit blocked: path={path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error":   "Too Many Requests",
                    "message": "Rate limit exceeded. Please wait 30 seconds before retrying.",
                    "code":    "RATE_LIMIT_EXCEEDED",
                },
                headers={
                    "Retry-After":          "30",
                    "X-RateLimit-Limit":    str(limit_used),
                    "X-RateLimit-Remaining":"0",
                }
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(limit_used)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
