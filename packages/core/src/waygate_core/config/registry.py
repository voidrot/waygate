from typing import TypeVar, Generic
from waygate_core.config.schema import CoreSettings
from waygate_core.plugin.manager import WayGatePluginManager, shared_plugin_manager
from waygate_core.plugin.registry import PluginGroups
from waygate_core.logging import get_logger
from pydantic_settings import BaseSettings

logger = get_logger()

PluginT = TypeVar("PluginT", bound=BaseSettings)


class ConfigRegistry(Generic[PluginT]):
    """
    Registry for settings classes.
    """

    def __init__(self, plugin_manager: WayGatePluginManager | None = None):
        self._registry = {}
        self._plugin_manager = plugin_manager or shared_plugin_manager
        self.register("core", CoreSettings)

    def discover(self) -> None:
        """
        Discover and register settings classes.
        """
        config_types = self._plugin_manager.get_plugin_configs(
            PluginGroups.all_groups()
        )

        for plugin_name, config_type in config_types.items():
            if plugin_name in self._registry:
                logger.warning(
                    f"Name for for plugin {plugin_name} is already registered, skipping.",
                    plugin_name=plugin_name,
                )
                continue

            self.register(plugin_name, config_type)

    def register(self, name: str, config: type[PluginT]) -> None:
        """
        Register a settings class.

        Args:
            name: The name to register the settings class under.
            config: The settings class to register.
        """
        self._registry[name] = config()

    def get(self, name) -> PluginT | None:
        """
        Get a registered settings class by name.

        Args:
            name: The name of the settings class to retrieve.

        Returns:
            The registered settings class, or None if not found.
        """
        return self._registry.get(name)
