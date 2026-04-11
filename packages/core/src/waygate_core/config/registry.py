from typing import TypeVar, Generic
from waygate_core.config.schema import CoreSettings
from waygate_core.plugin.base import WayGatePluginBase
from waygate_core.logging import get_logger
from pydantic_settings import BaseSettings
import importlib.metadata

logger = get_logger()

PluginT = TypeVar("PluginT", bound=BaseSettings)


class ConfigRegistry(Generic[PluginT]):
    """
    Registry for settings classes.
    """

    def __init__(self):
        self._registry = {}
        self.register("core", CoreSettings)

    def discover(self) -> None:
        """
        Discover and register settings classes.
        """
        entrypoints = importlib.metadata.entry_points(group="waygate.plugins")
        for ep in entrypoints:
            try:
                plugin_class = ep.load()
                if issubclass(plugin_class, WayGatePluginBase):
                    plugin_instance = plugin_class()
                    config = plugin_instance.config
                    if config is not None and issubclass(config, BaseSettings):
                        if plugin_instance.name in self._registry:
                            logger.warning(
                                f"Name for for plugin {plugin_instance.name} is already registered, skipping.",
                                plugin_name=plugin_instance.name,
                            )
                        else:
                            self.register(plugin_instance.name, config)
                            logger.info(
                                f"Registered config for plugin: {plugin_instance.name}"
                            )
                    if config is None:
                        logger.debug(
                            f"No config found for plugin: {plugin_instance.name}, skipping config registration."
                        )
                else:
                    logger.warning(
                        f"Plugin {ep.name} does not inherit from WayGatePluginBase, skipping config registration."
                    )
            except Exception as e:
                logger.error(f"Failed to load config from entry point {ep.name}: {e}")

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
