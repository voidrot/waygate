from waygate_web.settings import WaygateWebRuntimeSettings


def _clear_runtime_env(monkeypatch) -> None:
    for name in (
        "WAYGATE_WEB__HOST",
        "WAYGATE_WEB__PORT",
        "WAYGATE_WEB__TITLE",
        "WAYGATE_WEB__DESCRIPTION",
        "WAYGATE_WEB__VERSION",
        "HOST",
        "PORT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_runtime_settings_use_package_defaults(monkeypatch) -> None:
    _clear_runtime_env(monkeypatch)

    settings = WaygateWebRuntimeSettings()

    assert settings.host == "0.0.0.0"
    assert settings.port == 8080
    assert settings.title == "WayGate Web"
    assert settings.version == "0.1.0"


def test_runtime_settings_ignore_unprefixed_env_vars(monkeypatch) -> None:
    _clear_runtime_env(monkeypatch)
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9090")

    settings = WaygateWebRuntimeSettings()

    assert settings.host == "0.0.0.0"
    assert settings.port == 8080


def test_runtime_settings_accept_canonical_waygate_env_vars(monkeypatch) -> None:
    _clear_runtime_env(monkeypatch)
    monkeypatch.setenv("WAYGATE_WEB__HOST", "127.0.0.1")
    monkeypatch.setenv("WAYGATE_WEB__PORT", "9090")
    monkeypatch.setenv("WAYGATE_WEB__TITLE", "WayGate Operator")
    monkeypatch.setenv("WAYGATE_WEB__DESCRIPTION", "Configured description")
    monkeypatch.setenv("WAYGATE_WEB__VERSION", "0.2.0")

    settings = WaygateWebRuntimeSettings()

    assert settings.host == "127.0.0.1"
    assert settings.port == 9090
    assert settings.title == "WayGate Operator"
    assert settings.description == "Configured description"
    assert settings.version == "0.2.0"
