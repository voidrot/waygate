"""AuthTuna configuration for the unified web application."""

from __future__ import annotations

from os import getenv

from authtuna import init_app, init_settings
from fastapi import FastAPI

_DEV_FERNET_KEY = "2frEu1Z8ib60_6mFcq6VjA_CVxUeNbtOULgNtGx6uiE="
_DEV_JWT_SECRET = "waygate-web-dev-secret-change-me"


def configure_auth(app: FastAPI) -> None:
    """Initialize AuthTuna with local-safe defaults and environment overrides."""

    base_url = getenv(
        "WAYGATE_WEB_BASE_URL", getenv("API_BASE_URL", "http://localhost:8080")
    )

    init_settings(
        API_BASE_URL=base_url,
        APP_NAME="WayGate",
        STRATEGY=getenv("WAYGATE_WEB_AUTH_STRATEGY", "AUTO"),
        FERNET_KEYS=[getenv("WAYGATE_WEB_FERNET_KEY", _DEV_FERNET_KEY)],
        JWT_SECRET_KEY=getenv("WAYGATE_WEB_JWT_SECRET", _DEV_JWT_SECRET),
        SESSION_SECURE=getenv("WAYGATE_WEB_SESSION_SECURE", "false").lower() == "true",
        UI_ENABLED=True,
        dont_use_env=False,
    )
    init_app(app)
