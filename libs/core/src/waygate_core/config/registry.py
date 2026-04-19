"""Configuration registry that merges core and plugin settings.

The registry discovers plugin-provided Pydantic models and exposes them as a
single dynamic root settings object backed by environment variables.
"""

import re
from typing import TYPE_CHECKING, Any

from pydantic import Field, create_model
from pydantic_settings import BaseSettings, SettingsConfigDict

from waygate_core.config.schema import CoreSettings

if TYPE_CHECKING:
    from waygate_core.plugin.registry import WayGatePluginManager


class WaygateRootSettings(BaseSettings):
    """Root settings model containing core settings and plugin submodels."""

    core: CoreSettings = Field(default_factory=CoreSettings)

    model_config = SettingsConfigDict(
        env_prefix="WAYGATE_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )


def _normalize_name(name: str) -> str:
    """Normalize a plugin name for use in settings fields.

    Args:
        name: The plugin name to normalize.

    Returns:
        The normalized plugin name.
    """

    return re.sub(r"[^a-z0-9]", "_", name.lower())


class ConfigRegistry:
    """Discovers plugin config schemas and merges them into a single root settings object.

    Usage::

        registry = ConfigRegistry(shared_plugin_manager)
        settings = registry.build_config()
        # settings.core — core settings
        # settings.local_storage — LocalStorageConfig (if plugin is installed)
    """

    def __init__(self, plugin_manager: "WayGatePluginManager") -> None:
        self._plugin_manager = plugin_manager

    def build_config(self) -> WaygateRootSettings:
        """Build the merged root settings model.

        Each installed plugin that implements ``waygate_plugin_config`` gets a
        field on the returned object. Field names are normalized plugin names
        (for example ``local-storage`` becomes ``local_storage``), and the
        values are populated from ``WAYGATE_<PLUGIN_NAME>__<FIELD>`` variables.

        Returns:
            A root settings object containing core and plugin settings.
        """

        plugin_configs = self._plugin_manager.get_plugin_configs()

        if not plugin_configs:
            return WaygateRootSettings()

        extra_fields: dict[str, Any] = {}
        for name, config_cls in plugin_configs.items():
            normalized = _normalize_name(name)
            # Plugin names become root settings fields so env vars stay predictable.
            extra_fields[normalized] = (config_cls, Field(default_factory=config_cls))

        DynamicSettings = create_model(  # type: ignore[call-overload]
            "WaygateSettings",
            __base__=WaygateRootSettings,
            **extra_fields,
        )
        return DynamicSettings()
