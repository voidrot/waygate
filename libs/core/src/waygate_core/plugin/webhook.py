"""Webhook plugin contract used by the API ingress layer."""

from waygate_core.schema.document import RawDocument
from typing import Mapping
from pydantic import BaseModel
from abc import ABC, abstractmethod


class WebhookVerificationError(ValueError):
    """Raised when a webhook request fails authenticity or freshness checks."""


class WebhookPlugin(ABC):
    """Base class for webhook plugins.

    Webhook plugins are instantiated once at startup and cached process-wide.
    Implement webhook handlers as stateless where possible.
    """

    plugin_group: str = "waygate.plugins.webhooks"
    hook_name: str = "waygate_webhook_plugin"

    @property
    def name(self) -> str:
        """Return the plugin name.

        Returns:
            The plugin name.
        """
        return self.__class__.__name__

    @property
    def description(self) -> str:
        """Return a brief plugin description.

        Returns:
            The plugin description.
        """
        return "No description provided."

    @property
    def version(self) -> str:
        """Return the plugin version.

        Returns:
            The plugin version.
        """
        return "0.0.0"

    @abstractmethod
    async def handle_webhook(self, payload: dict) -> list[RawDocument]:
        """Handle an incoming webhook payload.

        Args:
            payload: The webhook payload to process.

        Returns:
            A list of raw documents produced from the payload.
        """
        raise NotImplementedError(
            "WebhookPlugin subclasses must implement handle_webhook"
        )

    @abstractmethod
    async def verify_webhook_request(
        self, headers: Mapping[str, str], body: bytes
    ) -> None:
        """Verify the incoming webhook request.

        Args:
            headers: The incoming request headers.
            body: The raw request body.

        Raises:
            NotImplementedError: This abstract method must be implemented by
                subclasses.
        """
        raise NotImplementedError(
            "WebhookPlugin subclasses must implement verify_webhook_request"
        )

    @abstractmethod
    async def enrich_webhook_payload(
        self, payload: dict, headers: Mapping[str, str]
    ) -> dict:
        """Enrich the incoming webhook payload.

        Args:
            payload: The original webhook payload.
            headers: The incoming request headers.

        Returns:
            The enriched payload passed to ``handle_webhook``.
        """
        return payload

    # --- OpenAPI metadata ---

    @property
    def openapi_summary(self) -> str:
        """Return the short OpenAPI summary.

        Returns:
            The route title shown in ``/docs``.
        """
        return self.name

    @property
    def openapi_payload_schema(self) -> type[BaseModel] | None:
        """Return the expected payload schema.

        Returns:
            A Pydantic model class describing the JSON body, or ``None`` when
            the body should remain untyped.
        """
        return None

    @property
    def openapi_response_schema(self) -> type[BaseModel] | None:
        """Return the success response schema.

        Returns:
            A Pydantic model class describing the success response body, or
            ``None`` when the default response should be used.
        """
        return None
