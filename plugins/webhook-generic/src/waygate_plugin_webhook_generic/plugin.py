from typing import Mapping

from pydantic import BaseModel

from waygate_core.plugin.hooks import PluginConfigRegistration, hookimpl
from waygate_core.plugin.webhook import WebhookPlugin
from waygate_core.schema.document import RawDocument

PLUGIN_NAME = "generic-webhook"


class GenericWebhookConfig(BaseModel):
    pass


class GenericWebhookPlugin(WebhookPlugin):
    plugin_name = PLUGIN_NAME

    def __init__(self, config: GenericWebhookConfig | None = None) -> None:
        self._config = config or GenericWebhookConfig()

    @staticmethod
    @hookimpl
    def waygate_webhook_plugin() -> type["GenericWebhookPlugin"]:
        return GenericWebhookPlugin

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        return PluginConfigRegistration(name=PLUGIN_NAME, config=GenericWebhookConfig)

    async def handle_webhook(self, payload: dict) -> list[RawDocument]:
        raise NotImplementedError

    async def verify_webhook_request(
        self, headers: Mapping[str, str], body: bytes
    ) -> None:
        pass

    async def enrich_webhook_payload(
        self, payload: dict, headers: Mapping[str, str]
    ) -> dict:
        return payload
