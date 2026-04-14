from __future__ import annotations
from abc import abstractmethod
from waygate_core.schema import RawDocument

from collections.abc import Mapping
from typing import TYPE_CHECKING

from waygate_core.plugin.base import WayGatePluginBase

if TYPE_CHECKING:
    from pydantic import BaseModel


class WebhookVerificationError(ValueError):
    """Raised when a webhook request fails authenticity or freshness checks."""


class WebhookPlugin(WayGatePluginBase):
    """
    Base class for webhook plugins.

    Webhook plugins are instantiated once at startup and cached process-wide.
    Implement webhook handlers as stateless where possible.
    """

    plugin_group: str = "waygate.plugins.webhooks"
    hook_name: str = "waygate_webhook_plugin"

    @abstractmethod
    async def handle_webhook(self, payload: dict) -> list[RawDocument]:
        """
        Handle an incoming webhook payload.

        Args:
            payload (dict): The webhook payload to process.
        """
        raise NotImplementedError(
            "WebhookPlugin subclasses must implement handle_webhook"
        )

    @abstractmethod
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

    @abstractmethod
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

    # --- OpenAPI metadata ---

    @property
    def openapi_summary(self) -> str:
        """Short summary shown as the route title in /docs. Defaults to the plugin name."""
        return self.name

    @property
    def openapi_payload_schema(self) -> type[BaseModel] | None:
        """Return a Pydantic model *class* describing the expected JSON body, or None to leave the body untyped."""
        return None

    @property
    def openapi_response_schema(self) -> type[BaseModel] | None:
        """Return a Pydantic model *class* describing the success response body, or None to use the default."""
        return None
