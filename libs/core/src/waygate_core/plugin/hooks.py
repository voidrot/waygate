"""Pluggy hooks and config-registration metadata for WayGate plugins."""

from dataclasses import dataclass
from waygate_core.plugin.communication import CommunicationClientPlugin
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
    """Registration record returned by ``waygate_plugin_config`` hooks."""

    name: str
    config: type[BaseModel]


class WayGatePluginSpec:
    @hookspec
    def waygate_webhook_plugin(self) -> type[WebhookPlugin] | WebhookPlugin | None:
        """Return a webhook plugin implementation.

        Returns:
            A webhook plugin class or instance, or ``None`` when not provided.
        """

    @hookspec
    def waygate_storage_plugin(self) -> type[StoragePlugin] | StoragePlugin | None:
        """Return a storage plugin implementation.

        Returns:
            A storage plugin class or instance, or ``None`` when not provided.
        """

    @hookspec
    def waygate_cron_plugin(self) -> type[CronPlugin] | CronPlugin | None:
        """Return a cron plugin implementation.

        Returns:
            A cron plugin class or instance, or ``None`` when not provided.
        """

    @hookspec
    def waygate_llm_provider_plugin(
        self,
    ) -> type[LLMProviderPlugin] | LLMProviderPlugin | None:
        """Return an LLM provider implementation.

        Returns:
            An LLM provider class or instance, or ``None`` when not provided.
        """

    @hookspec
    def waygate_communication_client_plugin(
        self,
    ) -> type[CommunicationClientPlugin] | CommunicationClientPlugin | None:
        """Return a communication client implementation.

        Returns:
            A communication client class or instance, or ``None`` when not
            provided.
        """

    @hookspec
    def waygate_plugin_config(self) -> PluginConfigRegistration | None:
        """Return plugin configuration registration metadata.

        Plugins opt in to config discovery by implementing this hook. The
        returned registration name is normalized and used as the field name on
        the root settings object (for example, ``local-storage`` becomes
        ``WAYGATE_LOCAL_STORAGE__*``).

        Returns:
            A plugin config registration record, or ``None`` when the plugin
            does not expose configuration.
        """


def resolve_plugin_hook_name(plugin_group: str) -> str:
    """Map a plugin group to its corresponding hook name.

    Args:
        plugin_group: The plugin group name.

    Returns:
        The corresponding hook name.

    Raises:
        ValueError: If the plugin group is unsupported.
    """

    hook_names = {
        "waygate.plugins.webhooks": "waygate_webhook_plugin",
        "waygate.plugins.storage": "waygate_storage_plugin",
        "waygate.plugins.llm": "waygate_llm_provider_plugin",
        "waygate.plugins.cron": "waygate_cron_plugin",
        "waygate.plugins.communication": "waygate_communication_client_plugin",
    }
    try:
        return hook_names[plugin_group]
    except KeyError as exc:
        raise ValueError(f"Unsupported plugin group: {plugin_group}") from exc
