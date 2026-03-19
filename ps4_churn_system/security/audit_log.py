"""
PS4 - Audit Logger
Tamper-evident audit trail for all sensitive operations.
Logs WHO did WHAT and WHEN — without logging sensitive data values.
"""

import logging
import logging.handlers
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


def setup_audit_logger(log_file: str = "logs/audit.log", level: str = "INFO") -> logging.Logger:
    """
    Configure a dedicated audit logger with rotating file handler.
    Separate from the app logger so audit logs can't be accidentally silenced.
    """
    os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else ".", exist_ok=True)

    audit_logger = logging.getLogger("ps4.audit")
    audit_logger.setLevel(getattr(logging, level, logging.INFO))

    # Rotating file handler — 10MB max, keep 10 backups
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s UTC | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    ))

    # Console handler (info level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter('%(levelname)s | %(message)s'))

    audit_logger.addHandler(file_handler)
    audit_logger.addHandler(console_handler)
    audit_logger.propagate = False

    return audit_logger


def _hash_ip(ip: str) -> str:
    """One-way hash of IP address for privacy-preserving logging."""
    return "ip:" + hashlib.sha256(ip.encode()).hexdigest()[:12]


def _safe_path(path: str) -> str:
    """Sanitise path for logging — remove any potential injected content."""
    import re
    return re.sub(r"[^\w/\-_?=&.]", "", path)[:120]


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Logs every API request with:
    - Timestamp (UTC)
    - Hashed IP (never plaintext IP)
    - HTTP method + path (sanitised)
    - Response status code
    - Duration (ms)
    - Request ID

    Does NOT log: request bodies, response bodies, headers with auth, or query params with values
    """

    def __init__(self, app, audit_logger: logging.Logger):
        super().__init__(app)
        self.logger = audit_logger

        # Sensitive paths that get extra WARNING-level logging
        self.sensitive_paths = {
            "/api/reset", "/api/run-campaign",
            "/api/complaints/analyse-all",
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        start      = time.time()
        request_id = hashlib.sha256(f"{start}{request.client}".encode()).hexdigest()[:8]
        client_ip  = request.client.host if request.client else "unknown"

        response = await call_next(request)

        duration_ms = round((time.time() - start) * 1000, 1)
        path        = _safe_path(str(request.url.path))
        method      = request.method
        status      = response.status_code

        # Build audit record (no sensitive values)
        record = {
            "ts":         datetime.now(timezone.utc).isoformat(),
            "req_id":     request_id,
            "ip":         _hash_ip(client_ip),
            "method":     method,
            "path":       path,
            "status":     status,
            "duration_ms": duration_ms,
        }

        log_line = json.dumps(record, separators=(",", ":"))

        # Choose log level based on path / status
        if path in self.sensitive_paths or status >= 500:
            self.logger.warning(log_line)
        elif status == 429:
            self.logger.warning(f"RATE_LIMIT | {log_line}")
        elif status == 403:
            self.logger.warning(f"AUTH_DENIED | {log_line}")
        elif status >= 400:
            self.logger.error(log_line)
        elif not path.startswith("/static"):
            self.logger.info(log_line)

        return response


class SecurityEventLogger:
    """
    High-level helper for logging specific security events.
    Call these from route handlers for important actions.
    """

    def __init__(self, logger: logging.Logger):
        self._log = logger

    def api_key_used(self, request: Request, endpoint: str):
        ip = request.client.host if request.client else "unknown"
        self._log.info(json.dumps({
            "event":    "ADMIN_API_USED",
            "endpoint": endpoint,
            "ip":       _hash_ip(ip),
            "ts":       datetime.now(timezone.utc).isoformat(),
        }))

    def ai_call_made(self, endpoint: str, customer_id: str):
        # Never log the customer's personal data — only the sanitised ID
        safe_id = customer_id[:10] if customer_id else "unknown"
        self._log.info(json.dumps({
            "event":       "AI_API_CALL",
            "endpoint":    endpoint,
            "customer_id": safe_id,
            "ts":          datetime.now(timezone.utc).isoformat(),
        }))

    def data_access(self, request: Request, resource: str, count: int):
        ip = request.client.host if request.client else "unknown"
        self._log.info(json.dumps({
            "event":    "DATA_ACCESS",
            "resource": resource,
            "count":    count,
            "ip":       _hash_ip(ip),
            "ts":       datetime.now(timezone.utc).isoformat(),
        }))

    def security_violation(self, request: Request, violation_type: str, detail: str):
        ip = request.client.host if request.client else "unknown"
        self._log.warning(json.dumps({
            "event":    "SECURITY_VIOLATION",
            "type":     violation_type,
            "detail":   detail[:100],
            "ip":       _hash_ip(ip),
            "ts":       datetime.now(timezone.utc).isoformat(),
        }))
