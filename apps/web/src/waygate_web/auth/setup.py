"""AuthTuna configuration for the unified web application."""

from __future__ import annotations

from authtuna import init_app, init_settings
from authtuna.core.config import Settings as AuthTunaSettings
from fastapi import FastAPI
from pydantic import Field, SecretStr
from pydantic_settings import SettingsConfigDict

_DEV_FERNET_KEY = "2frEu1Z8ib60_6mFcq6VjA_CVxUeNbtOULgNtGx6uiE="


class WaygateWebAuthSettings(AuthTunaSettings):
    """WayGate-scoped settings wrapper for the full AuthTuna config surface."""

    model_config = SettingsConfigDict(
        env_prefix="WAYGATE_WEB_AUTH__",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    APP_NAME: str = Field(default="WayGate")
    API_BASE_URL: str = Field(default="http://localhost:8080")
    STRATEGY: str = Field(default="AUTO")
    JWT_SECRET_KEY: SecretStr = Field(
        default=SecretStr("dev-secret-key-change-in-production")
    )
    FERNET_KEYS: list[SecretStr] = Field(
        default_factory=lambda: [SecretStr(_DEV_FERNET_KEY)]
    )
    SESSION_SECURE: bool = Field(default=False)


def _apply_auth_settings(settings: WaygateWebAuthSettings) -> None:
    init_settings(**settings.model_dump(), dont_use_env=True)


def configure_auth(
    app: FastAPI, *, settings: WaygateWebAuthSettings | None = None
) -> None:
    """Initialize AuthTuna using the typed web auth settings interface."""

    resolved_settings = settings or WaygateWebAuthSettings()

    _apply_auth_settings(resolved_settings)
    init_app(app)


async def initialize_auth_database(
    *,
    settings: WaygateWebAuthSettings | None = None,
    _db_manager: object | None = None,
) -> None:
    """Eagerly create AuthTuna tables during app startup when enabled."""

    resolved_settings = settings or WaygateWebAuthSettings()
    _apply_auth_settings(resolved_settings)

    db_manager = _db_manager
    if db_manager is None:
        from authtuna.core.database import db_manager as runtime_db_manager

        db_manager = runtime_db_manager

    if not resolved_settings.AUTO_CREATE_DATABASE:
        return

    if getattr(db_manager, "_initialized", False):
        return

    await db_manager.initialize_database()
    db_manager._initialized = True
