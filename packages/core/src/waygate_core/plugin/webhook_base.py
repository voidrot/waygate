from collections.abc import Mapping
from waygate_core.plugin.base import WayGatePluginBase


class WebhookVerificationError(ValueError):
    """Raised when a webhook request fails authenticity or freshness checks."""


class WebhookPlugin(WayGatePluginBase):
    """
    Base class for webhook plugins.
    """

    async def handle_webhook(self, payload: dict):
        """
        Handle an incoming webhook payload.

        Args:
            payload (dict): The webhook payload to process.
        """
        raise NotImplementedError(
            "WebhookPlugin subclasses must implement handle_webhook"
        )

    async def verify_webhook_request(
        self, headers: Mapping[str, str], body: bytes
    ) -> None:
        """
        Optionally verify the incoming webhook request (e.g. check signatures).

        Args:
            headers (Mapping[str, str]): The headers of the incoming request.
            body (Any): The raw body of the incoming request.

        Returns:
            bool: True if the request is valid, False otherwise.
        """
        raise NotImplementedError(
            "WebhookPlugin subclasses must implement verify_webhook_request"
        )

    async def enrich_webhook_payload(
        self, payload: dict, headers: Mapping[str, str]
    ) -> dict:
        """
        Optionally enrich the incoming webhook payload with additional data.

        Args:
            payload (dict): The original webhook payload.
            headers (Mapping[str, str]): The headers of the incoming request.

        Returns:
            dict: The enriched payload to be passed to handle_webhook.
        """
        return payload
