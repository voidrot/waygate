from dataclasses import dataclass
from waygate_core.plugin.llm import LLMProviderPlugin
from waygate_core.plugin.cron import CronPlugin
from waygate_core.plugin.storage import StoragePlugin
import pluggy
from pydantic import BaseModel
from waygate_core.plugin.webhook import WebhookPlugin

PROJECT_NAME = "waygate"

hookspec = pluggy.HookspecMarker(PROJECT_NAME)
hookimpl = pluggy.HookimplMarker(PROJECT_NAME)


@dataclass(frozen=True)
class PluginConfigRegistration:
    """Returned by waygate_plugin_config() hookimpls to register plugin config."""

    name: str
    config: type[BaseModel]


class WayGatePluginSpec:
    @hookspec
    def waygate_webhook_plugin(self) -> type[WebhookPlugin] | WebhookPlugin | None:
        """Return a WebhookPlugin class or instance to be registered with the WayGate API."""

    @hookspec
    def waygate_storage_plugin(self) -> type[StoragePlugin] | StoragePlugin | None:
        """Return a StoragePlugin class or instance to be registered with the WayGate API."""

    @hookspec
    def waygate_cron_plugin(self) -> type[CronPlugin] | CronPlugin | None:
        """Return a CronPlugin class or instance to be registered with the WayGate cron scheduler."""

    @hookspec
    def waygate_llm_provider_plugin(
        self,
    ) -> type[LLMProviderPlugin] | LLMProviderPlugin | None:
        """Return an LLMProviderPlugin class or instance to be registered with the WayGate LLM manager."""

    @hookspec
    def waygate_plugin_config(self) -> PluginConfigRegistration | None:
        """Return a PluginConfigRegistration to register plugin config with the core settings registry.

        Plugins opt-in to config discovery by implementing this hook. The returned
        PluginConfigRegistration.name is normalized and used as the field name on the
        root settings object (e.g. "local-storage" -> WAYGATE_LOCAL_STORAGE__*).
        """


def resolve_plugin_hook_name(plugin_group: str) -> str:
    hook_names = {
        "waygate.plugins.webhooks": "waygate_webhook_plugin",
        "waygate.plugins.storage": "waygate_storage_plugin",
        "waygate.plugins.llm": "waygate_llm_plugin",
        "waygate.plugins.cron": "waygate_cron_plugin",
    }
    try:
        return hook_names[plugin_group]
    except KeyError as exc:
        raise ValueError(f"Unsupported plugin group: {plugin_group}") from exc
