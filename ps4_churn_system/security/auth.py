"""
PS4 - API Key Authentication
Protects sensitive management endpoints with HMAC-verified API keys.
Keys are never logged or exposed in error messages.
"""

import hmac
import hashlib
import secrets
import logging
import time
from typing import Optional
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader

logger = logging.getLogger("ps4.auth")

# API key is read from the Authorization header: "Bearer <key>"
api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def _constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.
    Uses hmac.compare_digest which is resistant to timing side-channels.
    """
    return hmac.compare_digest(
        a.encode("utf-8"),
        b.encode("utf-8")
    )


class AuthManager:
    """
    Manages API key validation for admin-protected endpoints.
    """

    def __init__(self, admin_key: Optional[str] = None):
        self._admin_key = admin_key
        # Track failed auth attempts per IP (simple brute-force protection)
        self._failed_attempts: dict = {}
        self._lockout_until:   dict = {}

    def verify_admin_key(self, provided_key: Optional[str], client_ip: str) -> bool:
        """
        Verify an admin API key.
        Returns True if valid, False otherwise.
        Never reveals whether the key exists or why it failed.
        """
        now = time.time()

        # Check lockout
        ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:12]
        if ip_hash in self._lockout_until:
            if now < self._lockout_until[ip_hash]:
                logger.warning(f"Auth attempt during lockout from {ip_hash}")
                return False
            else:
                del self._lockout_until[ip_hash]
                self._failed_attempts.pop(ip_hash, None)

        # No admin key configured → admin routes are disabled
        if not self._admin_key:
            logger.warning("Admin key not configured — admin access denied")
            return False

        # No key provided
        if not provided_key:
            self._record_failure(ip_hash)
            return False

        # Constant-time comparison
        valid = _constant_time_compare(provided_key.strip(), self._admin_key)

        if valid:
            # Reset failure count on success
            self._failed_attempts.pop(ip_hash, None)
            logger.info(f"Admin auth success from {ip_hash}")
            return True
        else:
            self._record_failure(ip_hash)
            logger.warning(f"Admin auth failure from {ip_hash}")
            return False

    def _record_failure(self, ip_hash: str):
        """Track failed attempts and lock out after threshold."""
        self._failed_attempts[ip_hash] = self._failed_attempts.get(ip_hash, 0) + 1
        if self._failed_attempts[ip_hash] >= 5:
            # Lockout for 15 minutes after 5 failures
            self._lockout_until[ip_hash] = time.time() + 900
            logger.warning(f"IP {ip_hash} locked out for 15 minutes after repeated auth failures")


# Module-level auth manager — configured by app.py
_auth_manager: Optional[AuthManager] = None


def init_auth(admin_key: Optional[str]):
    global _auth_manager
    _auth_manager = AuthManager(admin_key)


def require_admin(
    request: Request,
    api_key: Optional[str] = Security(api_key_header)
) -> bool:
    """
    FastAPI dependency — use as: Depends(require_admin)
    Raises 403 if not authorised. Generic message to prevent info leakage.
    """
    if _auth_manager is None:
        raise HTTPException(status_code=503, detail="Auth system not initialised")

    client_ip = request.client.host if request.client else "unknown"

    if not _auth_manager.verify_admin_key(api_key, client_ip):
        raise HTTPException(
            status_code=403,
            detail="Access denied",  # Generic — never reveal why
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return True


def generate_secure_key(length: int = 32) -> str:
    """Generate a cryptographically secure random key."""
    return secrets.token_urlsafe(length)
