"""AuthTuna configuration for the unified web application."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any, cast

from authtuna import init_app, init_settings
from authtuna.core.config import Settings as AuthTunaSettings
from fastapi import FastAPI
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import SettingsConfigDict

_DEV_FERNET_KEY = "2frEu1Z8ib60_6mFcq6VjA_CVxUeNbtOULgNtGx6uiE="


def _resolve_template_directory(value: str) -> str:
    """Resolve package-relative template directories to filesystem paths."""

    candidate = Path(value)
    if candidate.is_absolute():
        return str(candidate)

    parts = candidate.parts
    if parts:
        package_name = parts[0]
        try:
            package_root = resources.files(package_name)
        except ModuleNotFoundError, TypeError:
            pass
        else:
            return str(package_root.joinpath(*parts[1:]))

    return str(candidate.resolve())


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
    UI_ENABLED: bool = Field(default=True)
    ADMIN_ROUTES_ENABLED: bool = Field(default=False)
    HTML_TEMPLATE_DIR: str = Field(default="waygate_web/templates/authtuna/auth")
    DASHBOARD_AND_USER_INFO_PAGES_TEMPLATE_DIR: str = Field(
        default="waygate_web/templates/authtuna/user"
    )
    EMAIL_TEMPLATE_DIR: str = Field(default="waygate_web/templates/authtuna/email")
    JWT_SECRET_KEY: SecretStr = Field(
        default=SecretStr("dev-secret-key-change-in-production")
    )
    FERNET_KEYS: list[SecretStr] = Field(
        default_factory=lambda: [SecretStr(_DEV_FERNET_KEY)]
    )
    SESSION_SECURE: bool = Field(default=False)

    @model_validator(mode="after")
    def resolve_template_directories(self) -> WaygateWebAuthSettings:
        self.HTML_TEMPLATE_DIR = _resolve_template_directory(self.HTML_TEMPLATE_DIR)
        self.DASHBOARD_AND_USER_INFO_PAGES_TEMPLATE_DIR = _resolve_template_directory(
            self.DASHBOARD_AND_USER_INFO_PAGES_TEMPLATE_DIR
        )
        self.EMAIL_TEMPLATE_DIR = _resolve_template_directory(self.EMAIL_TEMPLATE_DIR)
        return self


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

    runtime_db_manager = cast(Any, db_manager)

    if not resolved_settings.AUTO_CREATE_DATABASE:
        return

    if getattr(runtime_db_manager, "_initialized", False):
        return

    await runtime_db_manager.initialize_database()
    runtime_db_manager._initialized = True
