from types import SimpleNamespace

from fastapi import FastAPI
import pytest

from waygate_web.auth.setup import (
    WaygateWebAuthSettings,
    configure_auth,
    initialize_auth_database,
)


def _clear_auth_env(monkeypatch) -> None:
    for name in (
        "WAYGATE_WEB_AUTH__API_BASE_URL",
        "WAYGATE_WEB_AUTH__APP_NAME",
        "WAYGATE_WEB_AUTH__JWT_SECRET_KEY",
        "WAYGATE_WEB_AUTH__SESSION_SECURE",
        "WAYGATE_WEB_AUTH__STRATEGY",
        "WAYGATE_WEB_AUTH__UI_ENABLED",
        "WAYGATE_WEB_AUTH__DEFAULT_ADMIN_EMAIL",
        "WAYGATE_WEB_AUTH__THEME__MODE",
        "WAYGATE_WEB_AUTH__FERNET_KEYS",
        "JWT_SECRET_KEY",
        "API_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("WAYGATE_WEB_AUTH__APP_NAME", "WayGate")


def test_auth_settings_use_local_defaults_when_env_is_missing(monkeypatch) -> None:
    _clear_auth_env(monkeypatch)

    settings = WaygateWebAuthSettings()

    assert settings.API_BASE_URL == "http://localhost:8080"
    assert settings.APP_NAME == "WayGate"
    assert settings.STRATEGY == "AUTO"
    assert settings.SESSION_SECURE is False


def test_auth_settings_ignore_unprefixed_authtuna_env_vars(monkeypatch) -> None:
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("API_BASE_URL", "https://raw-authtuna.example.test")
    monkeypatch.setenv("JWT_SECRET_KEY", "raw-authtuna-secret")

    settings = WaygateWebAuthSettings()

    assert settings.API_BASE_URL == "http://localhost:8080"
    assert (
        settings.JWT_SECRET_KEY.get_secret_value()
        == "dev-secret-key-change-in-production"
    )


def test_auth_settings_accept_canonical_waygate_prefixed_env_vars(monkeypatch) -> None:
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("WAYGATE_WEB_AUTH__API_BASE_URL", "https://web.example.test")
    monkeypatch.setenv("WAYGATE_WEB_AUTH__APP_NAME", "WayGate Console")
    monkeypatch.setenv("WAYGATE_WEB_AUTH__JWT_SECRET_KEY", "prefixed-secret")
    monkeypatch.setenv("WAYGATE_WEB_AUTH__SESSION_SECURE", "true")
    monkeypatch.setenv("WAYGATE_WEB_AUTH__DEFAULT_ADMIN_EMAIL", "admin@waygate.test")
    monkeypatch.setenv("WAYGATE_WEB_AUTH__THEME__MODE", "single")
    monkeypatch.setenv("WAYGATE_WEB_AUTH__FERNET_KEYS", '["prefixed-fernet"]')

    settings = WaygateWebAuthSettings()

    assert settings.API_BASE_URL == "https://web.example.test"
    assert settings.APP_NAME == "WayGate Console"
    assert settings.JWT_SECRET_KEY.get_secret_value() == "prefixed-secret"
    assert settings.SESSION_SECURE is True
    assert settings.DEFAULT_ADMIN_EMAIL == "admin@waygate.test"
    assert settings.THEME.mode == "single"
    assert [key.get_secret_value() for key in settings.FERNET_KEYS] == [
        "prefixed-fernet"
    ]


def test_configure_auth_uses_resolved_settings(monkeypatch) -> None:
    _clear_auth_env(monkeypatch)

    calls: dict[str, object] = {}

    monkeypatch.setattr(
        "waygate_web.auth.setup.init_settings",
        lambda **kwargs: calls.update(kwargs),
    )
    monkeypatch.setattr(
        "waygate_web.auth.setup.init_app",
        lambda app: calls.update({"app": app}),
    )

    app = FastAPI()
    settings = WaygateWebAuthSettings(
        API_BASE_URL="https://web.example.test",
        STRATEGY="BEARER",
        JWT_SECRET_KEY="jwt-secret",
        FERNET_KEYS=["fernet-key"],
        SESSION_SECURE=True,
        ADMIN_ROUTES_ENABLED=False,
    )

    configure_auth(app, settings=settings)

    assert calls["API_BASE_URL"] == "https://web.example.test"
    assert calls["APP_NAME"] == "WayGate"
    assert calls["STRATEGY"] == "BEARER"
    assert [key.get_secret_value() for key in calls["FERNET_KEYS"]] == ["fernet-key"]
    assert calls["JWT_SECRET_KEY"].get_secret_value() == "jwt-secret"
    assert calls["SESSION_SECURE"] is True
    assert calls["ADMIN_ROUTES_ENABLED"] is False
    assert calls["UI_ENABLED"] is True
    assert calls["dont_use_env"] is True
    assert calls["app"] is app


@pytest.mark.anyio
async def test_initialize_auth_database_bootstraps_tables_on_startup(
    monkeypatch,
) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        "waygate_web.auth.setup.init_settings",
        lambda **kwargs: calls.update(kwargs),
    )

    async def fake_initialize_database() -> None:
        calls["initialize_database"] = True

    fake_db_manager = SimpleNamespace(
        _initialized=False,
        initialize_database=fake_initialize_database,
    )
    settings = WaygateWebAuthSettings(AUTO_CREATE_DATABASE=True)

    await initialize_auth_database(settings=settings, _db_manager=fake_db_manager)

    assert calls["dont_use_env"] is True
    assert calls["AUTO_CREATE_DATABASE"] is True
    assert calls["initialize_database"] is True
    assert fake_db_manager._initialized is True


@pytest.mark.anyio
async def test_initialize_auth_database_skips_bootstrap_when_disabled(
    monkeypatch,
) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        "waygate_web.auth.setup.init_settings",
        lambda **kwargs: calls.update(kwargs),
    )

    async def fake_initialize_database() -> None:
        calls["initialize_database"] = True

    fake_db_manager = SimpleNamespace(
        _initialized=False,
        initialize_database=fake_initialize_database,
    )
    settings = WaygateWebAuthSettings(AUTO_CREATE_DATABASE=False)

    await initialize_auth_database(settings=settings, _db_manager=fake_db_manager)

    assert calls["dont_use_env"] is True
    assert calls["AUTO_CREATE_DATABASE"] is False
    assert "initialize_database" not in calls
    assert fake_db_manager._initialized is False
