"""
PS4 - Secure Configuration Loader
Reads ALL sensitive values from environment variables or .env file.
Keys are NEVER hardcoded or logged.
"""

import os
import secrets
import logging
from pathlib import Path
from typing import Optional

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print("✅ Loaded .env file")
    else:
        load_dotenv()  # Try current directory
except ImportError:
    pass  # dotenv not installed — rely on system environment variables


def _require(key: str) -> str:
    """Get a required environment variable. Raise clear error if missing."""
    val = os.environ.get(key, "").strip()
    if not val:
        raise EnvironmentError(
            f"\n{'='*60}\n"
            f"❌  Missing required environment variable: {key}\n"
            f"    Copy .env.example → .env and fill in your values.\n"
            f"{'='*60}"
        )
    return val


def _optional(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


class Config:
    """Central secure configuration. All secrets loaded from environment."""

    # ── AI Keys ──────────────────────────────────────────────────────────────
    @staticmethod
    def anthropic_api_key() -> str:
        """Returns the Anthropic API key. Never logs or prints it."""
        return _optional("ANTHROPIC_API_KEY", "")

    @staticmethod
    def has_anthropic_key() -> bool:
        return bool(Config.anthropic_api_key())

    # ── App Security ─────────────────────────────────────────────────────────
    @staticmethod
    def secret_key() -> str:
        """Secret key for HMAC / token signing. Auto-generates if not set (ephemeral)."""
        key = _optional("SECRET_KEY", "")
        if not key:
            # Ephemeral key — safe for dev, warn loudly
            key = secrets.token_hex(32)
            logging.warning("⚠️  SECRET_KEY not set — using ephemeral key. Set it in .env for production.")
        return key

    @staticmethod
    def admin_api_key() -> Optional[str]:
        """Admin API key for protected endpoints. Optional — disables admin routes if absent."""
        return _optional("ADMIN_API_KEY", "") or None

    # ── Rate Limits ───────────────────────────────────────────────────────────
    @staticmethod
    def rate_limit_per_minute() -> int:
        return int(_optional("RATE_LIMIT_PER_MINUTE", "60"))

    @staticmethod
    def rate_limit_ai_per_minute() -> int:
        return int(_optional("RATE_LIMIT_AI_PER_MINUTE", "10"))

    # ── CORS ──────────────────────────────────────────────────────────────────
    @staticmethod
    def allowed_origins() -> list:
        raw = _optional("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:3000")
        return [o.strip() for o in raw.split(",") if o.strip()]

    # ── Server ────────────────────────────────────────────────────────────────
    @staticmethod
    def host() -> str:
        return _optional("HOST", "0.0.0.0")

    @staticmethod
    def port() -> int:
        return int(_optional("PORT", "8000"))

    @staticmethod
    def debug() -> bool:
        return _optional("DEBUG", "false").lower() == "true"

    # ── Logging ───────────────────────────────────────────────────────────────
    @staticmethod
    def audit_log_file() -> str:
        return _optional("AUDIT_LOG_FILE", "logs/audit.log")

    @staticmethod
    def log_level() -> str:
        return _optional("LOG_LEVEL", "INFO").upper()

    @staticmethod
    def summary() -> dict:
        """Returns a safe summary — NO secret values included."""
        return {
            "has_anthropic_key":     Config.has_anthropic_key(),
            "has_admin_key":         Config.admin_api_key() is not None,
            "has_secret_key":        bool(_optional("SECRET_KEY")),
            "rate_limit_general":    Config.rate_limit_per_minute(),
            "rate_limit_ai":         Config.rate_limit_ai_per_minute(),
            "allowed_origins_count": len(Config.allowed_origins()),
            "debug_mode":            Config.debug(),
        }


# Singleton instance
config = Config()
