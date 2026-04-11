from waygate_core.logging import get_logger
import importlib.metadata
from typing import Dict, Generic, TypeVar
from waygate_core.plugin.base import WayGatePluginBase
from dataclasses import dataclass

logger = get_logger()

PluginT = TypeVar("PluginT", bound=WayGatePluginBase)


@dataclass(frozen=True)
class PluginGroups:
    """
    A dataclass to hold plugin group names.
    """

    WEBHOOKS: str = "waygate.plugins.webhooks"
    CRON: str = "waygate.plugins.cron"
    STORAGE: str = "waygate.plugins.storage"
    LLM: str = "waygate.plugins.llm"


class PluginRegistry(Generic[PluginT]):
    def __init__(self, plugin_group: str, plugin_type: type[PluginT]):
        self._plugins: Dict[str, PluginT] = {}
        self._plugin_group = plugin_group
        self._plugin_type = plugin_type

    def register_plugins(self) -> None:
        entry_points = importlib.metadata.entry_points(group=self._plugin_group)
        for ep in entry_points:
            try:
                plugin_class = ep.load()
                plugin_instance = plugin_class()

                if not isinstance(plugin_instance, self._plugin_type):
                    logger.warning(
                        f"Plugin {ep.name} does not inherit from {self._plugin_type.__name__}, skipping.",
                        plugin_group=self._plugin_group,
                    )
                else:
                    self._plugins[plugin_instance.name] = plugin_instance
                    logger.info(
                        f"Registered plugin: {plugin_instance.name}",
                        plugin_group=self._plugin_group,
                    )

            except Exception as e:
                logger.error(
                    f"Failed to load plugin {ep.name}: {e}",
                    plugin_group=self._plugin_group,
                )

    def get(self, name: str) -> PluginT | None:
        return self._plugins.get(name)

    def get_all(self) -> Dict[str, PluginT]:
        return dict(self._plugins)
