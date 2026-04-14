from pydantic import Field, create_model
from waygate_core.config.schema import CoreSettings
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from waygate_core.plugin.manager import WayGatePluginManager, shared_plugin_manager
from waygate_core.plugin.registry import PluginGroups
from waygate_core.logging import get_logger

logger = get_logger()


class WaygateRootSettings(BaseSettings):
    core: CoreSettings = Field(default_factory=CoreSettings)

    model_config = SettingsConfigDict(
        env_prefix="WAYGATE_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )


class ConfigRegistry:
    def __init__(self, plugin_manager: WayGatePluginManager | None = None):
        self._plugin_manager = plugin_manager or shared_plugin_manager
        self._config_instance: WaygateRootSettings | None = None

    def build_config(self) -> WaygateRootSettings:
        if self._config_instance is not None:
            return self._config_instance

        fields: dict[str, Any] = {
            "core": (CoreSettings, Field(default_factory=CoreSettings))
        }

        plugin_schemas = self._plugin_manager.get_plugin_configs(
            PluginGroups.all_groups()
        )
        for namespace, schema_class in plugin_schemas.items():
            # Normalize plugin name to a valid Python identifier so pydantic-settings
            # can construct a valid env var name (e.g. "local-storage" -> "local_storage"
            # maps to WAYGATE_LOCAL_STORAGE__*).
            field_name = namespace.replace("-", "_")
            fields[field_name] = (schema_class, Field(default_factory=schema_class))

        settings_model = create_model(
            "WaygateRootSettings",
            __base__=WaygateRootSettings,
            **fields,
        )

        self._config_instance = settings_model()
        logger.debug(
            "Configuration loaded successfully",
            config=self._config_instance.model_dump(),
        )
        return self._config_instance
