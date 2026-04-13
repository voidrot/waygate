from typing import Dict, Generic, TypeVar
from waygate_core.plugin.base import WayGatePluginBase
from waygate_core.plugin.manager import WayGatePluginManager, shared_plugin_manager
from dataclasses import dataclass

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

    @classmethod
    def all_groups(cls) -> tuple[str, str, str, str]:
        return (cls.WEBHOOKS, cls.CRON, cls.STORAGE, cls.LLM)


class PluginRegistry(Generic[PluginT]):
    def __init__(
        self,
        plugin_group: str,
        plugin_type: type[PluginT],
        plugin_manager: WayGatePluginManager | None = None,
    ):
        self._plugins: Dict[str, PluginT] = {}
        self._plugin_group = plugin_group
        self._plugin_type = plugin_type
        self._plugin_manager = plugin_manager or shared_plugin_manager

    def register_plugins(self) -> None:
        self._plugins = self._plugin_manager.get_plugins(
            self._plugin_group,
            self._plugin_type,
        )

    def get(self, name: str) -> PluginT | None:
        return self._plugins.get(name)

    def get_all(self) -> Dict[str, PluginT]:
        return dict(self._plugins)
