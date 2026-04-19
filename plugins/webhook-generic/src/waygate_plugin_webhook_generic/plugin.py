"""Generic webhook ingestion plugin for WayGate."""

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone

from pydantic import BaseModel, ValidationError
from uuid_utils import uuid4

from waygate_core.plugin.hooks import PluginConfigRegistration, hookimpl
from waygate_core.plugin.webhook import WebhookPlugin
from waygate_core.schema.document import RawDocument
from waygate_core.schema.visibility import Visibility

from waygate_plugin_webhook_generic import __VERSION__
from waygate_plugin_webhook_generic.models import GenericWebhookPayload

PLUGIN_NAME = "generic-webhook"


class GenericWebhookConfig(BaseModel):
    """Configuration for the generic webhook plugin."""

    pass


class GenericWebhookPlugin(WebhookPlugin):
    """Validate generic webhook payloads and emit RawDocument records."""

    plugin_name = PLUGIN_NAME

    def __init__(self, config: GenericWebhookConfig | None = None) -> None:
        """Initialize the generic webhook plugin.

        Args:
            config: Optional plugin configuration.
        """

        self._config = config or GenericWebhookConfig()

    @staticmethod
    @hookimpl
    def waygate_webhook_plugin() -> type["GenericWebhookPlugin"]:
        """Register the generic webhook implementation.

        Returns:
            The plugin class to register with Pluggy.
        """

        return GenericWebhookPlugin

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        """Register the plugin configuration model.

        Returns:
            The plugin config registration metadata.
        """

        return PluginConfigRegistration(name=PLUGIN_NAME, config=GenericWebhookConfig)

    @property
    def name(self) -> str:
        """Return the canonical plugin name.

        Returns:
            The plugin name used for registration and lookups.
        """

        return PLUGIN_NAME

    @property
    def description(self) -> str:
        """Return a short human-readable description.

        Returns:
            A description of the webhook adapter.
        """

        return (
            "A generic webhook plugin for WayGate that validates structured "
            "payloads and emits RawDocument records."
        )

    @property
    def version(self) -> str:
        """Return the plugin version.

        Returns:
            The package version string.
        """

        return __VERSION__

    @property
    def openapi_payload_schema(self) -> type[BaseModel]:
        """Return the request payload schema exposed to OpenAPI.

        Returns:
            The Pydantic model describing the webhook payload.
        """

        return GenericWebhookPayload

    async def handle_webhook(self, payload: dict) -> list[RawDocument]:
        """Validate and convert a webhook payload into raw documents.

        Args:
            payload: The incoming webhook payload.

        Returns:
            RawDocument records extracted from the payload.

        Raises:
            ValueError: If the payload does not match the expected schema.
        """

        try:
            validated = GenericWebhookPayload.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Invalid generic webhook payload: {exc}") from exc

        return self._build_documents_from_payload(validated)

    async def verify_webhook_request(
        self, headers: Mapping[str, str], body: bytes
    ) -> None:
        """Verify the webhook request.

        Args:
            headers: The incoming request headers.
            body: The raw request body.
        """

        pass

    async def enrich_webhook_payload(
        self, payload: dict, headers: Mapping[str, str]
    ) -> dict:
        """Return the payload unchanged for downstream processing.

        Args:
            payload: The incoming payload.
            headers: The incoming request headers.

        Returns:
            The unmodified payload.
        """

        return payload

    def _build_documents_from_payload(
        self, payload: GenericWebhookPayload
    ) -> list[RawDocument]:
        """Build raw documents from a validated webhook payload."""

        timestamp = _parse_originated_at(payload.metadata.originated_at)
        documents: list[RawDocument] = []

        for document in payload.documents:
            document_metadata = document.metadata or {}
            merged_topics = _merge_unique(
                payload.metadata.topics,
                _coerce_metadata_list(document_metadata, "topics"),
            )
            merged_tags = _merge_unique(
                payload.metadata.tags,
                _coerce_metadata_list(document_metadata, "tags"),
            )

            # Each payload document becomes one raw record in the storage layer.
            documents.append(
                RawDocument(
                    source_type=PLUGIN_NAME,
                    source_id=document.document_name,
                    source_uri=document.document_path,
                    source_hash=document.document_hash,
                    doc_id=str(uuid4()),
                    timestamp=timestamp,
                    content=document.content,
                    topics=merged_topics,
                    tags=merged_tags,
                    visibility=Visibility.PUBLIC,
                )
            )

        return documents


def _coerce_metadata_list(metadata: dict[str, object], key: str) -> list[str]:
    """Coerce a metadata field into a list of strings.

    Args:
        metadata: Metadata dictionary to inspect.
        key: Metadata key to coerce.

    Returns:
        A list of strings.

    Raises:
        ValueError: If the value is not a list of strings.
    """

    raw_value = metadata.get(key, [])
    if raw_value is None:
        return []
    if not isinstance(raw_value, list):
        raise ValueError(f"Document metadata '{key}' must be a list of strings")

    values: list[str] = []
    for value in raw_value:
        if not isinstance(value, str):
            raise ValueError(f"Document metadata '{key}' must be a list of strings")
        values.append(value)
    return values


def _merge_unique(primary: Sequence[str] | None, secondary: Sequence[str]) -> list[str]:
    """Merge two sequences while preserving first-seen order and uniqueness."""

    merged: list[str] = []
    seen: set[str] = set()

    for value in [*(primary or []), *secondary]:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)

    return merged


def _parse_originated_at(originated_at: str | None) -> datetime:
    """Parse an originated-at timestamp and normalize it to UTC.

    Args:
        originated_at: The optional timestamp string.

    Returns:
        A timezone-aware UTC datetime.

    Raises:
        ValueError: If the timestamp is malformed or missing timezone data.
    """

    if originated_at is None:
        return datetime.now(timezone.utc)

    normalized = originated_at.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            "Invalid originated_at timestamp, expected ISO-8601 format"
        ) from exc

    if parsed.tzinfo is None:
        raise ValueError("Invalid originated_at timestamp, timezone is required")

    return parsed.astimezone(timezone.utc)
