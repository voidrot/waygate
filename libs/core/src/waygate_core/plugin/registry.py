import re

import pluggy
from pydantic import BaseModel

from waygate_core.plugin.hooks import (
    PROJECT_NAME,
    PluginConfigRegistration,
    WayGatePluginSpec,
)

PLUGIN_GROUPS = (
    "waygate.plugins.webhooks",
    "waygate.plugins.storage",
    "waygate.plugins.llm",
    "waygate.plugins.cron",
    "waygate.plugins.communication",
)

_GROUP_HOOK_ATTR: dict[str, str] = {
    "waygate.plugins.webhooks": "waygate_webhook_plugin",
    "waygate.plugins.storage": "waygate_storage_plugin",
    "waygate.plugins.llm": "waygate_llm_provider_plugin",
    "waygate.plugins.cron": "waygate_cron_plugin",
    "waygate.plugins.communication": "waygate_communication_client_plugin",
}


def normalize_plugin_name(name: str) -> str:
    """Normalize a plugin name for use in settings and lookups.

    Args:
        name: The plugin name to normalize.

    Returns:
        The normalized plugin name.
    """

    return re.sub(r"[^a-z0-9]", "_", name.lower())


class WayGatePluginManager:
    """Manage plugin loading, config discovery, and instantiation via Pluggy."""

    def __init__(self) -> None:
        """Initialize the shared plugin manager."""

        self._pm = pluggy.PluginManager(PROJECT_NAME)
        self._pm.add_hookspecs(WayGatePluginSpec)
        self._loaded: set[str] = set()

    def load_all(self) -> None:
        """Load all supported plugin groups from setuptools entry points."""

        for group in PLUGIN_GROUPS:
            if group not in self._loaded:
                self._pm.load_setuptools_entrypoints(group)
                self._loaded.add(group)

    def get_plugin_configs(self) -> dict[str, type[BaseModel]]:
        """Collect configuration models from installed plugins.

        Returns:
            A mapping of plugin name to config model class.
        """

        configs: dict[str, type[BaseModel]] = {}
        for registration in self._pm.hook.waygate_plugin_config():
            if registration and isinstance(registration, PluginConfigRegistration):
                configs[registration.name] = registration.config
        return configs

    def _instantiate_plugins(
        self, hook_attr: str, settings: object
    ) -> dict[str, object]:
        """Instantiate plugins for a hook and inject resolved config objects.

        Args:
            hook_attr: The Pluggy hook attribute to resolve.
            settings: The merged WayGate settings object.

        Returns:
            A mapping of plugin instance name to instantiated plugin.
        """

        hook = getattr(self._pm.hook, hook_attr)

        config_map: dict[str, object] = {}
        for name in self.get_plugin_configs():
            normalized = normalize_plugin_name(name)
            config_instance = getattr(settings, normalized, None)
            if config_instance is not None:
                config_map[normalized] = config_instance

        plugins: dict[str, object] = {}
        for plugin_cls in hook():
            if plugin_cls is None:
                continue

            plugin_name = getattr(plugin_cls, "plugin_name", None)
            if plugin_name:
                config = config_map.get(normalize_plugin_name(plugin_name))
                instance = plugin_cls(config) if config is not None else plugin_cls()
            else:
                instance = plugin_cls()

            key = getattr(instance, "name", plugin_cls.__name__)
            plugins[key] = instance

        return plugins

    def get_plugins(self, group: str, settings: object) -> dict[str, object]:
        """Instantiate plugins for a group and inject resolved config objects.

        Args:
            group: The plugin group to load.
            settings: The merged WayGate settings object.

        Returns:
            A mapping of plugin instance name to instantiated plugin.
        """

        return self._instantiate_plugins(_GROUP_HOOK_ATTR[group], settings)

    def get_plugins_for_hook(
        self, hook_attr: str, settings: object
    ) -> dict[str, object]:
        """Instantiate plugins exposed through an explicit Pluggy hook."""

        return self._instantiate_plugins(hook_attr, settings)


shared_plugin_manager = WayGatePluginManager()
