from waygate_core.schema.document import RawDocument
from typing import Mapping
from pydantic import BaseModel
from abc import ABC, abstractmethod


class WebhookPlugin(ABC):
    """
    Base class for webhook plugins.

    Webhook plugins are instantiated once at startup and cached process-wide.
    Implement webhook handlers as stateless where possible.
    """

    plugin_group: str = "waygate.plugins.webhooks"
    hook_name: str = "waygate_webhook_plugin"

    @property
    def name(self) -> str:
        """
        The name of the plugin.

        Returns:
            str: The name of the plugin.
        """
        return self.__class__.__name__

    @property
    def description(self) -> str:
        """
        A brief description of the plugin.

        Returns:
            str: A description of the plugin.
        """
        return "No description provided."

    @property
    def version(self) -> str:
        """
        The version of the plugin.

        Returns:
            str: The version of the plugin.
        """
        return "0.0.0"

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
