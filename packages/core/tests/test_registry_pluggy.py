from pydantic_settings import BaseSettings
import pluggy

from waygate_core.config.registry import ConfigRegistry
from waygate_core.plugin import PluginConfigRegistration, WayGatePluginManager, hookimpl
from waygate_core.plugin.base import WayGatePluginBase
from waygate_core.plugin.registry import PluginGroups, PluginRegistry
from waygate_core.plugin.webhook_base import WebhookPlugin


class _ValidPlugin(WebhookPlugin):
    @property
    def name(self) -> str:
        return "valid-plugin"

    async def handle_webhook(self, payload: dict) -> list:
        return []

    async def verify_webhook_request(self, headers, body: bytes) -> None:
        return None

    async def enrich_webhook_payload(self, payload: dict, headers) -> dict:
        return payload


class _InvalidPlugin:
    pass


class _WebhookHookPlugin:
    @staticmethod
    @hookimpl
    def waygate_webhook_plugin() -> type[WayGatePluginBase]:
        return _ValidPlugin


class _InvalidWebhookHookPlugin:
    @staticmethod
    @hookimpl
    def waygate_webhook_plugin() -> type[_InvalidPlugin]:
        return _InvalidPlugin


class _TestSettings(BaseSettings):
    enabled: bool = True


class _ConfigPlugin(WayGatePluginBase):
    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        return PluginConfigRegistration(name="config-plugin", config=_TestSettings)

    @property
    def name(self) -> str:
        return "config-plugin"


class _NoConfigPlugin(WayGatePluginBase):
    @property
    def name(self) -> str:
        return "no-config-plugin"


def test_plugin_registry_uses_pluggy_entrypoint_loading(
    monkeypatch,
) -> None:
    loaded_groups: list[str] = []

    def _fake_load(self, group: str) -> int:
        loaded_groups.append(group)
        self.register(_WebhookHookPlugin, name="valid")
        self.register(_InvalidWebhookHookPlugin, name="invalid")
        return 2

    monkeypatch.setattr(
        pluggy.PluginManager,
        "load_setuptools_entrypoints",
        _fake_load,
    )

    registry = PluginRegistry(
        PluginGroups.WEBHOOKS,
        plugin_manager=WayGatePluginManager(),
    )

    registry.register_plugins()

    assert loaded_groups == list(PluginGroups.all_groups())
    assert registry.get("valid-plugin") is not None
    assert registry.get("invalid") is None


def test_config_registry_discovers_configs_via_plugin_registry(
    monkeypatch,
) -> None:
    def _fake_load(self, group: str) -> int:
        if group == PluginGroups.WEBHOOKS:
            self.register(_ConfigPlugin, name="config-plugin")
            self.register(_NoConfigPlugin, name="no-config-plugin")
        return 2

    monkeypatch.setattr(
        pluggy.PluginManager,
        "load_setuptools_entrypoints",
        _fake_load,
    )

    registry = ConfigRegistry(plugin_manager=WayGatePluginManager())

    config = registry.build_config()

    dumped = config.model_dump()
    assert config.core is not None
    assert "config_plugin" in dumped
    assert dumped["config_plugin"]["enabled"] is True
    assert "no_config_plugin" not in dumped


def test_real_webhook_plugin_is_discovered_via_pluggy() -> None:
    registry = PluginRegistry(PluginGroups.WEBHOOKS)

    registry.register_plugins()

    plugin = registry.get("generic-webhook")
    assert plugin is not None
    assert plugin.name == "generic-webhook"


def test_real_storage_plugin_and_config_are_discovered_via_pluggy() -> None:
    registry = PluginRegistry(PluginGroups.STORAGE)

    registry.register_plugins()

    plugin = registry.get("local-storage")
    assert plugin is not None

    config_registry = ConfigRegistry()
    config = config_registry.build_config()

    assert "local_storage" in config.model_dump()


def test_real_llm_plugin_and_config_are_discovered_via_pluggy() -> None:
    registry = PluginRegistry(PluginGroups.LLM)

    registry.register_plugins()

    plugin = registry.get("OllamaProvider")
    assert plugin is not None

    config_registry = ConfigRegistry()
    config = config_registry.build_config()

    assert "OllamaProvider" in config.model_dump()


def test_shared_plugin_manager_loads_each_group_once(monkeypatch) -> None:
    loaded_groups: list[str] = []
    plugin_manager = WayGatePluginManager()

    def _fake_load(self, group: str) -> int:
        loaded_groups.append(group)
        self.register(_WebhookHookPlugin, name=f"{group}-valid")
        return 1

    monkeypatch.setattr(
        pluggy.PluginManager,
        "load_setuptools_entrypoints",
        _fake_load,
    )

    first_registry = PluginRegistry(
        PluginGroups.WEBHOOKS,
        plugin_manager=plugin_manager,
    )
    second_registry = PluginRegistry(
        PluginGroups.WEBHOOKS,
        plugin_manager=plugin_manager,
    )

    first_registry.register_plugins()
    second_registry.register_plugins()

    assert loaded_groups == list(PluginGroups.all_groups())
