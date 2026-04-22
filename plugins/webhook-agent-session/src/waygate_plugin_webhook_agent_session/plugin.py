"""Dedicated completed agent-session webhook ingestion plugin for WayGate."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Mapping, Sequence
from urllib.parse import quote

from pydantic import BaseModel, Field, SecretStr, ValidationError, field_validator

from waygate_core.plugin import PluginConfigRegistration, WorkflowTriggerMessage
from waygate_core.plugin.hooks import hookimpl
from waygate_core.plugin.webhook import WebhookPlugin, WebhookVerificationError
from waygate_core.schema.document import RawDocument, SourceMetadataBase

from waygate_plugin_webhook_agent_session import __VERSION__
from waygate_plugin_webhook_agent_session.models import AgentSessionWebhookPayload

PLUGIN_NAME = "agent-session"


class AgentSessionWebhookConfig(BaseModel):
    """Configuration for the dedicated agent-session webhook plugin."""

    signing_secret: SecretStr | None = Field(default=None)
    allow_unsigned: bool = Field(default=False)
    max_timestamp_skew_seconds: int = Field(default=300, ge=0)

    @field_validator("signing_secret")
    @classmethod
    def _reject_blank_signing_secret(
        cls,
        value: SecretStr | None,
    ) -> SecretStr | None:
        """Reject blank shared secrets so signing is never silently weakened."""

        if value is not None and not value.get_secret_value().strip():
            raise ValueError("signing_secret must not be blank")
        return value


class AgentSessionWebhookPlugin(WebhookPlugin):
    """Validate and ingest completed agent-session payloads."""

    plugin_name = PLUGIN_NAME

    def __init__(self, config: AgentSessionWebhookConfig | None = None) -> None:
        """Initialize the agent-session webhook plugin.

        Args:
            config: Optional plugin configuration.
        """

        self._config = config or AgentSessionWebhookConfig()

    @staticmethod
    @hookimpl
    def waygate_webhook_plugin() -> type["AgentSessionWebhookPlugin"]:
        """Register the webhook plugin implementation."""

        return AgentSessionWebhookPlugin

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        """Register the plugin configuration model."""

        return PluginConfigRegistration(
            name=PLUGIN_NAME,
            config=AgentSessionWebhookConfig,
        )

    @property
    def name(self) -> str:
        """Return the canonical plugin name."""

        return PLUGIN_NAME

    @property
    def description(self) -> str:
        """Return a short human-readable description."""

        return "Webhook plugin for completed agent-session transcript ingestion"

    @property
    def version(self) -> str:
        """Return the plugin version."""

        return __VERSION__

    @property
    def openapi_summary(self) -> str:
        """Return the short OpenAPI summary."""

        return "Agent session webhook"

    @property
    def openapi_payload_schema(self) -> type[BaseModel]:
        """Return the OpenAPI request schema."""

        return AgentSessionWebhookPayload

    async def verify_webhook_request(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> None:
        """Verify the incoming webhook request.

        Requests are verified with an HMAC signature when a signing secret is
        configured. Unsigned requests are only allowed when explicitly enabled.
        """

        secret = self._config.signing_secret
        if secret is None:
            if self._config.allow_unsigned:
                return
            raise WebhookVerificationError(
                "Agent-session webhooks require signing unless allow_unsigned is enabled"
            )

        timestamp = _get_header(headers, "X-Waygate-Timestamp")
        signature = _get_header(headers, "X-Waygate-Signature")
        if timestamp is None or signature is None:
            raise WebhookVerificationError(
                "Missing X-Waygate-Timestamp or X-Waygate-Signature header"
            )

        timestamp_value = _parse_unix_timestamp(timestamp)
        now = int(time.time())
        if abs(now - timestamp_value) > self._config.max_timestamp_skew_seconds:
            raise WebhookVerificationError(
                "Webhook timestamp is outside the allowed replay window"
            )

        expected_signature = hmac.new(
            secret.get_secret_value().encode("utf-8"),
            timestamp.encode("utf-8") + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        provided_signature = signature.strip()
        if provided_signature.startswith("sha256="):
            provided_signature = provided_signature[7:]

        if not hmac.compare_digest(provided_signature, expected_signature):
            raise WebhookVerificationError("Webhook signature verification failed")

    async def enrich_webhook_payload(
        self,
        payload: dict,
        headers: Mapping[str, str],
    ) -> dict:
        """Return the payload unchanged for downstream processing."""

        return payload

    async def handle_webhook(self, payload: dict) -> list[RawDocument]:
        """Validate and convert a completed session payload into a raw artifact."""

        try:
            validated = AgentSessionWebhookPayload.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Invalid agent-session payload: {exc}") from exc

        canonical_payload = _canonical_payload(validated)
        pretty_payload = _pretty_payload(validated)
        source_hash = (
            f"sha256:{hashlib.sha256(canonical_payload.encode('utf-8')).hexdigest()}"
        )
        source_uri = validated.session.conversation_url or _build_synthetic_session_uri(
            validated.provider,
            validated.session.session_id,
        )
        metadata = SourceMetadataBase.model_validate(
            {
                "kind": "agent-session",
                "provider": validated.provider,
                "surface": validated.surface,
                "capture_adapter": validated.capture_adapter,
                "schema_version": validated.schema_version,
                "session_id": validated.session.session_id,
            }
        )

        document = RawDocument(
            source_type=PLUGIN_NAME,
            source_id=validated.session.session_id,
            source_uri=source_uri,
            source_hash=source_hash,
            source_metadata=metadata,
            timestamp=validated.session.completed_at,
            topics=_dedupe_values(validated.session.topics),
            tags=_dedupe_values(
                [
                    *validated.session.tags,
                    "agent-session",
                    f"provider:{validated.provider}",
                    f"surface:{validated.surface}",
                    f"adapter:{validated.capture_adapter}",
                ]
            ),
            visibility=validated.visibility,
            content=pretty_payload,
        )
        return [document]

    def build_workflow_trigger(
        self,
        payload: dict,
        document_paths: list[str],
    ) -> WorkflowTriggerMessage | None:
        """Build the compile trigger for a completed session upload."""

        session = payload["session"]
        return WorkflowTriggerMessage(
            event_type="draft.ready",
            source="waygate-web.webhooks.agent-session",
            document_paths=document_paths,
            idempotency_key=f"{payload['provider']}:{session['session_id']}",
            metadata={
                "session_id": session["session_id"],
                "provider": str(payload["provider"]),
                "surface": str(payload["surface"]),
                "capture_adapter": str(payload["capture_adapter"]),
                "schema_version": str(payload["schema_version"]),
            },
        )


def _get_header(headers: Mapping[str, str], name: str) -> str | None:
    """Return a case-insensitive header value."""

    target = name.casefold()
    for header_name, header_value in headers.items():
        if header_name.casefold() == target:
            return header_value
    return None


def _parse_unix_timestamp(value: str) -> int:
    """Parse a Unix epoch seconds header."""

    try:
        return int(value)
    except ValueError as exc:
        raise WebhookVerificationError(
            "X-Waygate-Timestamp must be Unix epoch seconds"
        ) from exc


def _canonical_payload(payload: AgentSessionWebhookPayload) -> str:
    """Return the canonical compact JSON form used for hashing."""

    dumped = payload.model_dump(mode="json", exclude_none=True)
    return json.dumps(dumped, sort_keys=True, separators=(",", ":"))


def _pretty_payload(payload: AgentSessionWebhookPayload) -> str:
    """Return the stored JSON transcript bundle."""

    dumped = payload.model_dump(mode="json", exclude_none=True)
    return json.dumps(dumped, sort_keys=True, indent=2) + "\n"


def _build_synthetic_session_uri(provider: str, session_id: str) -> str:
    """Build a synthetic source URI when no canonical conversation URL exists."""

    return f"agent-session://{quote(provider, safe='')}/{quote(session_id, safe='')}"


def _dedupe_values(values: Sequence[str]) -> list[str]:
    """Normalize and deduplicate text values while preserving order."""

    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return merged
