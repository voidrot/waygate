from waygate_core.config.registry import WaygateRootSettings
from waygate_core.plugin.registry import WayGatePluginManager


def test_communication_plugin_discovery_from_entry_points() -> None:
    manager = WayGatePluginManager()
    manager.load_all()

    plugins = manager.get_plugins(
        "waygate.plugins.communication", WaygateRootSettings()
    )

    assert "communication-http" in plugins
