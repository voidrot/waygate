from waygate_core.config.registry import ConfigRegistry, WaygateRootSettings
from waygate_core.plugin.registry import WayGatePluginManager


def test_communication_plugin_discovery_from_entry_points() -> None:
    manager = WayGatePluginManager()
    manager.load_all()

    plugins = manager.get_plugins(
        "waygate.plugins.communication", WaygateRootSettings()
    )

    assert "communication-http" in plugins


def test_llm_plugin_config_injection_uses_plugin_name_attribute(
    monkeypatch,
) -> None:
    manager = WayGatePluginManager()
    manager.load_all()

    monkeypatch.setenv("WAYGATE_OLLAMAPROVIDER__BASE_URL", "http://ollama.local/")
    monkeypatch.setenv("WAYGATE_OLLAMAPROVIDER__VALIDATE_MODEL_ON_INIT", "true")

    settings = ConfigRegistry(manager).build_config()
    plugins = manager.get_plugins("waygate.plugins.llm", settings)

    provider = plugins["OllamaProvider"]

    assert provider._config.base_url == "http://ollama.local"
    assert provider._config.validate_model_on_init is True


def test_optional_llm_plugin_config_does_not_break_root_settings() -> None:
    manager = WayGatePluginManager()
    manager.load_all()

    settings = ConfigRegistry(manager).build_config()

    assert hasattr(settings, "featherlessaiprovider")
    assert settings.featherlessaiprovider.featherless_api_key is None


def test_featherless_llm_plugin_config_injection_uses_plugin_name_attribute(
    monkeypatch,
) -> None:
    manager = WayGatePluginManager()
    manager.load_all()

    monkeypatch.setenv("WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_API_KEY", "test-key")
    monkeypatch.setenv(
        "WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_BASE_URL",
        "https://featherless.invalid/v1/",
    )

    settings = ConfigRegistry(manager).build_config()
    plugins = manager.get_plugins("waygate.plugins.llm", settings)

    provider = plugins["FeatherlessAIProvider"]

    assert provider._config.featherless_api_key is not None
    assert provider._config.featherless_api_key.get_secret_value() == "test-key"
    assert provider._config.featherless_base_url == "https://featherless.invalid/v1"
