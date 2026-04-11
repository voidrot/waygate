from collections.abc import Mapping
from waygate_core.schema import RawDocument
from waygate_core.plugin import WebhookPlugin
from . import __version__


class GenericWebhookProvider(WebhookPlugin):
    @property
    def name(self) -> str:
        return "generic-webhook"

    @property
    def description(self) -> str:
        return "A generic webhook plugin for WayGate that can be configured to handle various webhook payloads."

    @property
    def version(self) -> str:
        return __version__

    async def handle_webhook(self, payload: dict) -> list[RawDocument]:
        # For demonstration purposes, we'll just log the payload.
        # In a real implementation, you would add logic here to process the webhook payload as needed.
        print(f"Received webhook payload: {payload}")
        return []

    async def verify_webhook_request(
        self, headers: Mapping[str, str], body: bytes
    ) -> None:
        # For demonstration purposes, we'll just accept all requests.
        # In a real implementation, you would add logic here to verify the request (e.g. check signatures).
        return None
