from typing import Dict, Generic, Literal, TypeVar, cast, overload
from waygate_core.plugin.base import WayGatePluginBase
from waygate_core.plugin.cron_base import CronPlugin
from waygate_core.plugin.llm_base import BaseLLMProvider
from waygate_core.plugin.manager import WayGatePluginManager, shared_plugin_manager
from waygate_core.plugin.storage_base import StoragePlugin
from waygate_core.plugin.webhook_base import WebhookPlugin
from dataclasses import dataclass

PluginT = TypeVar("PluginT", bound=WayGatePluginBase)


@dataclass(frozen=True)
class PluginGroups:
    """
    A dataclass to hold plugin group names.
    """

    WEBHOOKS: Literal["waygate.plugins.webhooks"] = "waygate.plugins.webhooks"
    CRON: Literal["waygate.plugins.cron"] = "waygate.plugins.cron"
    STORAGE: Literal["waygate.plugins.storage"] = "waygate.plugins.storage"
    LLM: Literal["waygate.plugins.llm"] = "waygate.plugins.llm"

    @classmethod
    def all_groups(cls) -> tuple[str, str, str, str]:
        return (cls.WEBHOOKS, cls.CRON, cls.STORAGE, cls.LLM)


class PluginRegistry(Generic[PluginT]):
    @overload
    def __init__(
        self: "PluginRegistry[WebhookPlugin]",
        plugin_group: Literal["waygate.plugins.webhooks"],
        plugin_manager: WayGatePluginManager | None = None,
    ): ...

    @overload
    def __init__(
        self: "PluginRegistry[StoragePlugin]",
        plugin_group: Literal["waygate.plugins.storage"],
        plugin_manager: WayGatePluginManager | None = None,
    ): ...

    @overload
    def __init__(
        self: "PluginRegistry[BaseLLMProvider]",
        plugin_group: Literal["waygate.plugins.llm"],
        plugin_manager: WayGatePluginManager | None = None,
    ): ...

    @overload
    def __init__(
        self: "PluginRegistry[CronPlugin]",
        plugin_group: Literal["waygate.plugins.cron"],
        plugin_manager: WayGatePluginManager | None = None,
    ): ...

    @overload
    def __init__(
        self: "PluginRegistry[WayGatePluginBase]",
        plugin_group: str,
        plugin_manager: WayGatePluginManager | None = None,
    ): ...

    def __init__(
        self,
        plugin_group: str,
        plugin_manager: WayGatePluginManager | None = None,
    ):
        self._plugins: Dict[str, PluginT] = {}
        self._plugin_group = plugin_group
        self._plugin_manager = plugin_manager or shared_plugin_manager

        plugin_types: dict[str, type[WayGatePluginBase]] = {
            PluginGroups.WEBHOOKS: WebhookPlugin,
            PluginGroups.STORAGE: StoragePlugin,
            PluginGroups.LLM: BaseLLMProvider,
            PluginGroups.CRON: CronPlugin,
        }
        self._plugin_type = plugin_types.get(plugin_group, WayGatePluginBase)

    def register_plugins(self) -> None:
        resolved = self._plugin_manager.get_plugins(self._plugin_group)
        filtered = {
            name: plugin
            for name, plugin in resolved.items()
            if isinstance(plugin, self._plugin_type)
        }
        self._plugins = cast(Dict[str, PluginT], filtered)

    def get(self, name: str) -> PluginT | None:
        return self._plugins.get(name)

    def get_all(self) -> Dict[str, PluginT]:
        return dict(self._plugins)
