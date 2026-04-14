from __future__ import annotations
from pydantic import BaseModel

from dataclasses import dataclass

import pluggy

from waygate_core.plugin.base import WayGatePluginBase
from waygate_core.plugin.cron_base import CronPlugin
from waygate_core.plugin.llm_base import BaseLLMProvider
from waygate_core.plugin.storage_base import StoragePlugin
from waygate_core.plugin.webhook_base import WebhookPlugin

PROJECT_NAME = "waygate"

hookspec = pluggy.HookspecMarker(PROJECT_NAME)
hookimpl = pluggy.HookimplMarker(PROJECT_NAME)


@dataclass(frozen=True)
class PluginConfigRegistration:
    name: str
    config: type[BaseModel]


class WayGatePluginSpec:
    @hookspec
    def waygate_webhook_plugin(self) -> type[WebhookPlugin] | WebhookPlugin | None:
        """Return the webhook plugin implementation for registration."""

    @hookspec
    def waygate_storage_plugin(self) -> type[StoragePlugin] | StoragePlugin | None:
        """Return the storage plugin implementation for registration."""

    @hookspec
    def waygate_llm_plugin(self) -> type[BaseLLMProvider] | BaseLLMProvider | None:
        """Return the llm plugin implementation for registration."""

    @hookspec
    def waygate_cron_plugin(self) -> type[CronPlugin] | CronPlugin | None:
        """Return the cron plugin implementation for registration."""

    @hookspec
    def waygate_plugin_config(self) -> PluginConfigRegistration | None:
        """Return explicit plugin config registration metadata."""


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


def coerce_plugin_instance(
    candidate: type[WayGatePluginBase] | WayGatePluginBase | None,
) -> WayGatePluginBase | None:
    if candidate is None:
        return None
    if isinstance(candidate, type):
        return candidate()
    return candidate
