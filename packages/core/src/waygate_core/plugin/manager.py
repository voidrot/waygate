from __future__ import annotations

from typing import Dict, TypeVar

import pluggy
from pydantic_settings import BaseSettings

from waygate_core.logging import get_logger
from waygate_core.plugin.base import WayGatePluginBase
from waygate_core.plugin.hooks import (
    PluginConfigRegistration,
    WayGatePluginSpec,
    coerce_plugin_instance,
    resolve_plugin_hook_name,
)

logger = get_logger()

PluginT = TypeVar("PluginT", bound=WayGatePluginBase)


class WayGatePluginManager:
    def __init__(self) -> None:
        self._manager = pluggy.PluginManager("waygate")
        self._manager.add_hookspecs(WayGatePluginSpec)
        self._loaded_groups: set[str] = set()
        self._plugin_cache: dict[str, dict[str, WayGatePluginBase]] = {}
        self._config_cache: dict[str, type[BaseSettings]] | None = None

    def load_group(self, plugin_group: str) -> None:
        if plugin_group in self._loaded_groups:
            return

        try:
            self._manager.load_setuptools_entrypoints(plugin_group)
        except Exception as e:
            logger.error(
                f"Failed to load plugin group {plugin_group}: {e}",
                plugin_group=plugin_group,
            )
        finally:
            self._loaded_groups.add(plugin_group)

    def load_groups(self, plugin_groups: tuple[str, ...]) -> None:
        for plugin_group in plugin_groups:
            self.load_group(plugin_group)

    def get_plugins(
        self,
        plugin_group: str,
        plugin_type: type[PluginT],
    ) -> Dict[str, PluginT]:
        self.load_group(plugin_group)

        if plugin_group not in self._plugin_cache:
            hook_name = resolve_plugin_hook_name(plugin_group)
            hook_caller = getattr(self._manager.hook, hook_name)
            resolved_plugins: dict[str, WayGatePluginBase] = {}

            for plugin_object in hook_caller():
                try:
                    plugin_instance = coerce_plugin_instance(plugin_object)

                    if plugin_instance is None:
                        continue

                    if not isinstance(plugin_instance, plugin_type):
                        logger.warning(
                            f"Plugin {plugin_instance.__class__.__name__} does not inherit from {plugin_type.__name__}, skipping.",
                            plugin_group=plugin_group,
                        )
                        continue

                    if plugin_instance.name in resolved_plugins:
                        logger.warning(
                            f"Plugin {plugin_instance.name} is already registered, skipping duplicate.",
                            plugin_group=plugin_group,
                            plugin_name=plugin_instance.name,
                        )
                        continue

                    resolved_plugins[plugin_instance.name] = plugin_instance
                    logger.info(
                        f"Registered plugin: {plugin_instance.name}",
                        plugin_group=plugin_group,
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to load plugin from hook {hook_name}: {e}",
                        plugin_group=plugin_group,
                    )

            self._plugin_cache[plugin_group] = resolved_plugins

        return {
            name: plugin
            for name, plugin in self._plugin_cache[plugin_group].items()
            if isinstance(plugin, plugin_type)
        }

    def get_plugin_configs(
        self,
        plugin_groups: tuple[str, ...],
    ) -> dict[str, type[BaseSettings]]:
        self.load_groups(plugin_groups)

        if self._config_cache is None:
            resolved_configs: dict[str, type[BaseSettings]] = {}

            for registration in self._manager.hook.waygate_plugin_config():
                if registration is None:
                    continue

                try:
                    if not isinstance(registration, PluginConfigRegistration):
                        logger.warning(
                            "Plugin config registration has invalid type, skipping."
                        )
                        continue

                    if registration.name in resolved_configs:
                        logger.warning(
                            f"Name for for plugin {registration.name} is already registered, skipping.",
                            plugin_name=registration.name,
                        )
                        continue

                    if not issubclass(registration.config, BaseSettings):
                        logger.warning(
                            f"Config for plugin {registration.name} does not inherit from BaseSettings, skipping.",
                            plugin_name=registration.name,
                        )
                        continue

                    resolved_configs[registration.name] = registration.config
                    logger.info(
                        f"Registered config for plugin: {registration.name}",
                        plugin_name=registration.name,
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to register config from hook: {e}",
                    )

            self._config_cache = resolved_configs

        return dict(self._config_cache)


shared_plugin_manager = WayGatePluginManager()
