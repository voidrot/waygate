from waygate_core.config.registry import ConfigRegistry
from waygate_plugin_communication_http.plugin import CommunicationHttpConfig


class _FakePluginManager:
    def get_plugin_configs(self):
        return {"communication-http": CommunicationHttpConfig}


def test_plugin_config_uses_plugin_namespace(monkeypatch) -> None:
    monkeypatch.setenv(
        "WAYGATE_COMMUNICATION_HTTP__ENDPOINT",
        "http://127.0.0.1:9000/workflows/trigger",
    )

    settings = ConfigRegistry(_FakePluginManager()).build_config()

    assert (
        settings.communication_http.endpoint
        == "http://127.0.0.1:9000/workflows/trigger"
    )
    assert not hasattr(settings.core, "endpoint")


def test_core_selector_stays_in_core_namespace(monkeypatch) -> None:
    monkeypatch.setenv("WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME", "communication-http")

    settings = ConfigRegistry(_FakePluginManager()).build_config()

    assert settings.core.communication_plugin_name == "communication-http"
