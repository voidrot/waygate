from types import SimpleNamespace

from waygate_core import bootstrap as bootstrap_module


def test_bootstrap_app_populates_process_cache(monkeypatch) -> None:
    fake_manager = SimpleNamespace(
        load_all=lambda: None,
        get_plugins=lambda group, settings: {},
    )

    class FakeConfigRegistry:
        def __init__(self, plugin_manager) -> None:
            self._plugin_manager = plugin_manager

        def build_config(self):
            return SimpleNamespace(core=SimpleNamespace())

    monkeypatch.setattr(bootstrap_module, "configure_logging", lambda: None)
    monkeypatch.setattr(
        "waygate_core.config.registry.ConfigRegistry", FakeConfigRegistry
    )
    monkeypatch.setattr(
        "waygate_core.plugin.registry.shared_plugin_manager", fake_manager
    )
    monkeypatch.setattr(bootstrap_module, "_app_context", None)

    app_context = bootstrap_module.bootstrap_app()

    assert bootstrap_module.get_app_context() is app_context
    assert bootstrap_module.bootstrap_app() is app_context
