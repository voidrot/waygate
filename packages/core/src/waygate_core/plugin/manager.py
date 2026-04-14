from __future__ import annotations

from typing import Any, Dict, Literal, cast, overload

import pluggy
from pydantic import BaseModel

from waygate_core.logging import get_logger
from waygate_core.plugin.base import WayGatePluginBase
from waygate_core.plugin.cron_base import CronPlugin
from waygate_core.plugin.hooks import (
    PluginConfigRegistration,
    WayGatePluginSpec,
    coerce_plugin_instance,
    resolve_plugin_hook_name,
)
from waygate_core.plugin.llm_base import BaseLLMProvider
from waygate_core.plugin.storage_base import StoragePlugin
from waygate_core.plugin.webhook_base import WebhookPlugin

logger = get_logger()

SUPPORTED_PLUGIN_GROUPS: tuple[str, str, str, str] = (
    "waygate.plugins.webhooks",
    "waygate.plugins.cron",
    "waygate.plugins.storage",
    "waygate.plugins.llm",
)

WebhookGroup = Literal["waygate.plugins.webhooks"]
CronGroup = Literal["waygate.plugins.cron"]
StorageGroup = Literal["waygate.plugins.storage"]
LlmGroup = Literal["waygate.plugins.llm"]


class WayGatePluginManager:
    """
    Centralized plugin discovery, loading, and lifecycle management via pluggy.

    The WayGatePluginManager consolidates all entry-point loading and plugin instance
    caching into a single process-wide singleton. Plugins are discovered once at
    application startup and cached for the lifetime of the process.

    **Caching & Lifecycle:**

    - Plugin instances per group are cached ([group][plugin_name] → instance)
    - Plugin configs are cached globally ({plugin_name} → PluginConfigRegistration)
    - Instances are created once via coerce_plugin_instance() and reused
    - All consumers share the same cached instances

    **Thread Safety:**

    The manager itself is thread-safe for querying cached data (read-only after init).
    Plugin developers should ensure their plugin implementations are thread-safe,
    as the same plugin instance may be called concurrently by multiple components.
    """

    def __init__(self) -> None:
        self._manager = pluggy.PluginManager("waygate")
        self._manager.add_hookspecs(WayGatePluginSpec)
        self._loaded_groups: set[str] = set()
        self._plugin_cache: dict[str, dict[str, WayGatePluginBase]] = {}
        self._config_cache: dict[str, type[BaseModel]] | None = None

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

    @overload
    def get_plugins(self, plugin_group: WebhookGroup) -> Dict[str, WebhookPlugin]: ...

    @overload
    def get_plugins(self, plugin_group: StorageGroup) -> Dict[str, StoragePlugin]: ...

    @overload
    def get_plugins(self, plugin_group: LlmGroup) -> Dict[str, BaseLLMProvider]: ...

    @overload
    def get_plugins(self, plugin_group: CronGroup) -> Dict[str, CronPlugin]: ...

    @overload
    def get_plugins(self, plugin_group: str) -> Dict[str, WayGatePluginBase]: ...

    def get_plugins(self, plugin_group: str) -> Dict[str, WayGatePluginBase]:
        # Ensure a single manager instance eagerly loads all supported plugin groups once.
        self.load_groups(SUPPORTED_PLUGIN_GROUPS)

        if plugin_group not in self._plugin_cache:
            self._load_plugin_group(plugin_group)

        return dict(self._plugin_cache[plugin_group])

    def _load_plugin_group(self, plugin_group: str, app_config: object = None) -> None:
        """Discover and instantiate plugins for *plugin_group*.

        When *app_config* is supplied each plugin is re-instantiated with its
        named settings field (looked up via ``name.replace('-', '_')``), so
        env-var values reach the plugin constructor in a single pass rather
        than requiring a separate reconfiguration step.
        """
        hook_name = resolve_plugin_hook_name(plugin_group)
        hook_caller = getattr(self._manager.hook, hook_name)
        resolved_plugins: dict[str, WayGatePluginBase] = {}

        for plugin_object in hook_caller():
            try:
                plugin_instance = coerce_plugin_instance(plugin_object)

                if plugin_instance is None:
                    continue

                if plugin_instance.name in resolved_plugins:
                    logger.warning(
                        f"Plugin {plugin_instance.name} is already registered, skipping duplicate.",
                        plugin_group=plugin_group,
                        plugin_name=plugin_instance.name,
                    )
                    continue

                if app_config is not None:
                    field_name = plugin_instance.name.replace("-", "_")
                    plugin_config = getattr(app_config, field_name, None)
                    if plugin_config is not None:
                        try:
                            plugin_cls = cast("type[Any]", type(plugin_instance))
                            plugin_instance = plugin_cls(plugin_config)
                        except Exception:
                            logger.warning(
                                "Could not pass config to plugin, using default instance",
                                plugin_name=plugin_instance.name,
                            )

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

    def configure_from_settings(self, app_config: object) -> None:
        """Populate the plugin cache with config-aware instances in one pass.

        Must be called after :meth:`get_plugin_configs` has loaded all entry
        points (i.e., after ``ConfigRegistry.build_config()``).  Subsequent
        :meth:`get_plugins` calls will return the cached configured instances
        without re-discovering or re-instantiating anything.
        """
        for group in SUPPORTED_PLUGIN_GROUPS:
            if group in self._plugin_cache:
                continue  # already populated (e.g., called twice)
            self._load_plugin_group(group, app_config=app_config)

    def get_plugin_configs(
        self,
        plugin_groups: tuple[str, ...],
    ) -> dict[str, type[BaseModel]]:
        self.load_groups(plugin_groups)

        if self._config_cache is None:
            resolved_configs: dict[str, type[BaseModel]] = {}

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

                    if not issubclass(registration.config, BaseModel):
                        logger.warning(
                            f"Config for plugin {registration.name} does not inherit from BaseModel, skipping.",
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
