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

    monkeypatch.setenv("WAYGATE_OLLAMAPROVIDER__BASE_URL", "http://ollama.local")

    settings = ConfigRegistry(manager).build_config()
    plugins = manager.get_plugins("waygate.plugins.llm", settings)

    provider = plugins["OllamaProvider"]

    assert provider._config.base_url == "http://ollama.local"
