"""
config.py – Central application configuration, driven by environment variables.

Local development works out of the box with safe defaults. Production must
provide real secrets via environment variables; missing critical settings
cause startup to fail loudly rather than running insecurely.
"""

import os

# "development" (default) or "production"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

# ─── JWT signing key ──────────────────────────────────────────────────
# In production a SECRET_KEY MUST be supplied; we never fall back to a
# public default there (that would let anyone forge tokens).
_DEV_SECRET = "dev-insecure-secret-do-not-use-in-production"
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY environment variable must be set in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    SECRET_KEY = _DEV_SECRET

# ─── CORS ─────────────────────────────────────────────────────────────
# Comma-separated list of allowed origins, e.g. "https://app.guleed.no".
# Defaults to "*" for local development.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

# ─── Demo data seeding ────────────────────────────────────────────────
# Auto-seed demo users/parts on startup. Enabled by default in development,
# disabled by default in production (set SEED_ON_STARTUP=true to override).
SEED_ON_STARTUP = os.getenv("SEED_ON_STARTUP", "false" if IS_PRODUCTION else "true").lower() == "true"
