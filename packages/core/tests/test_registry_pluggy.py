from pydantic_settings import BaseSettings
import pluggy

from waygate_core.config.registry import ConfigRegistry
from waygate_core.plugin import PluginConfigRegistration, WayGatePluginManager, hookimpl
from waygate_core.plugin.base import WayGatePluginBase
from waygate_core.plugin.llm_base import BaseLLMProvider
from waygate_core.plugin.storage_base import StoragePlugin
from waygate_core.plugin.webhook_base import WebhookPlugin
from waygate_core.plugin.registry import PluginGroups, PluginRegistry


class _ValidPlugin(WayGatePluginBase):
    @property
    def name(self) -> str:
        return "valid-plugin"


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
        WayGatePluginBase,
        plugin_manager=WayGatePluginManager(),
    )

    registry.register_plugins()

    assert loaded_groups == [PluginGroups.WEBHOOKS]
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

    registry.discover()

    assert registry.get("core") is not None
    config = registry.get("config-plugin")
    assert config is not None
    assert isinstance(config, _TestSettings)
    assert registry.get("no-config-plugin") is None


def test_real_webhook_plugin_is_discovered_via_pluggy() -> None:
    registry = PluginRegistry(PluginGroups.WEBHOOKS, WebhookPlugin)

    registry.register_plugins()

    plugin = registry.get("generic-webhook")
    assert plugin is not None
    assert plugin.name == "generic-webhook"


def test_real_storage_plugin_and_config_are_discovered_via_pluggy() -> None:
    registry = PluginRegistry(PluginGroups.STORAGE, StoragePlugin)

    registry.register_plugins()

    plugin = registry.get("local-storage")
    assert plugin is not None

    config_registry = ConfigRegistry()
    config_registry.discover()

    assert config_registry.get("local-storage") is not None


def test_real_llm_plugin_and_config_are_discovered_via_pluggy() -> None:
    registry = PluginRegistry(PluginGroups.LLM, BaseLLMProvider)

    registry.register_plugins()

    plugin = registry.get("OllamaProvider")
    assert plugin is not None

    config_registry = ConfigRegistry()
    config_registry.discover()

    assert config_registry.get("OllamaProvider") is not None


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
        WayGatePluginBase,
        plugin_manager=plugin_manager,
    )
    second_registry = PluginRegistry(
        PluginGroups.WEBHOOKS,
        WayGatePluginBase,
        plugin_manager=plugin_manager,
    )

    first_registry.register_plugins()
    second_registry.register_plugins()

    assert loaded_groups == [PluginGroups.WEBHOOKS]
