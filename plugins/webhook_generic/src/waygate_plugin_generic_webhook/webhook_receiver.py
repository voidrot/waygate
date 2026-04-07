import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from waygate_core.plugin_base import IngestionPlugin
from waygate_core.schemas import RawDocument, SourceMetadataBase


class WebhookReceiver(IngestionPlugin):
    @property
    def plugin_name(self) -> str:
        return "generic_webhook"

    def handle_webhook(self, payload: dict) -> list[RawDocument]:
        documents_payload, defaults = self._extract_documents(payload)
        if not documents_payload:
            raise ValueError("Webhook body cannot be empty")
        return [
            self._build_document(item, defaults=defaults, index=index)
            for index, item in enumerate(documents_payload)
        ]

    def _extract_documents(self, payload: Any) -> tuple[list[Any], dict[str, Any]]:
        if isinstance(payload, dict) and isinstance(payload.get("documents"), list):
            return payload["documents"], payload
        if isinstance(payload, list):
            return payload, {}
        return [payload], payload if isinstance(payload, dict) else {}

    def _build_document(
        self, payload: Any, defaults: dict[str, Any], index: int
    ) -> RawDocument:
        self._ensure_value_present(payload)
        if not isinstance(payload, dict):
            payload = {"content": payload}

        source_type = self._first_string(payload, "source_type", "type")
        if source_type is None:
            source_type = self._first_string(defaults, "source_type", "type")
        if source_type is None:
            source_type = self.plugin_name
        source_type = source_type.lower()

        source_id = self._resolve_source_id(payload, defaults, index)
        timestamp = self._resolve_timestamp(payload, defaults)
        tags = self._resolve_tags(payload, defaults)
        content = self._resolve_content(payload)
        source_url = self._resolve_source_url(payload, defaults)
        source_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        source_metadata = self._resolve_source_metadata(
            payload=payload, defaults=defaults
        )

        return RawDocument(
            source_type=source_type,
            source_id=source_id,
            timestamp=timestamp,
            content=content,
            tags=tags,
            source_url=source_url,
            source_hash=source_hash,
            source_metadata=source_metadata,
        )

    def _resolve_source_url(
        self, payload: dict[str, Any], defaults: dict[str, Any]
    ) -> str | None:
        return self._first_string(
            payload,
            "source_url",
            "url",
            "link",
            "html_url",
            "permalink",
        ) or self._first_string(
            defaults,
            "source_url",
            "url",
            "link",
            "html_url",
            "permalink",
        )

    def _resolve_source_metadata(
        self, payload: dict[str, Any], defaults: dict[str, Any]
    ) -> SourceMetadataBase | None:
        merged = {**defaults, **payload}
        raw_source_metadata = merged.get("source_metadata")
        if isinstance(raw_source_metadata, dict):
            try:
                return SourceMetadataBase.model_validate(raw_source_metadata)
            except (TypeError, ValueError):
                return None
        return None

    def _resolve_source_id(
        self, payload: dict[str, Any], defaults: dict[str, Any], index: int
    ) -> str:
        source_id = self._first_string(
            payload,
            "source_id",
            "id",
            "event_id",
            "delivery_id",
            "message_id",
        )
        if source_id is not None:
            return source_id

        default_source_id = self._first_string(
            defaults,
            "source_id",
            "id",
            "event_id",
            "delivery_id",
            "message_id",
        )
        if default_source_id is not None:
            documents = defaults.get("documents")
            if isinstance(documents, list) and len(documents) > 1:
                return f"{default_source_id}:{index}"
            return default_source_id

        return str(uuid4())

    def _resolve_timestamp(
        self, payload: dict[str, Any], defaults: dict[str, Any]
    ) -> datetime:
        timestamp_value = self._first_value(
            payload,
            "timestamp",
            "created_at",
            "occurred_at",
            "event_time",
            "time",
        )
        if timestamp_value is None:
            timestamp_value = self._first_value(
                defaults,
                "timestamp",
                "created_at",
                "occurred_at",
                "event_time",
                "time",
            )

        if isinstance(timestamp_value, datetime):
            timestamp = timestamp_value
        elif isinstance(timestamp_value, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp_value, tz=UTC)
        elif isinstance(timestamp_value, str):
            timestamp = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now(UTC)

        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=UTC)
        return timestamp

    def _resolve_tags(
        self, payload: dict[str, Any], defaults: dict[str, Any]
    ) -> list[str]:
        tag_value = payload.get("tags", defaults.get("tags", []))
        if tag_value is None:
            return []
        if isinstance(tag_value, str):
            return [tag_value]
        if isinstance(tag_value, list):
            return [str(tag) for tag in tag_value]
        return [str(tag_value)]

    def _resolve_content(self, payload: dict[str, Any]) -> str:
        for key in ("content", "body", "text", "message"):
            value = payload.get(key)
            if value is None:
                continue
            self._ensure_value_present(value)
            if isinstance(value, str):
                return value
            return json.dumps(value, sort_keys=True)
        return json.dumps(payload, sort_keys=True)

    def _ensure_value_present(self, value: Any) -> None:
        if value is None:
            raise ValueError("Webhook body cannot be empty")
        if isinstance(value, str) and not value.strip():
            raise ValueError("Webhook body cannot be empty")
        if isinstance(value, (dict, list)) and not value:
            raise ValueError("Webhook body cannot be empty")

    def _first_string(self, payload: dict[str, Any], *keys: str) -> str | None:
        value = self._first_value(payload, *keys)
        if value is None:
            return None
        return str(value)

    def _first_value(self, payload: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in payload and payload[key] is not None:
                return payload[key]
        return None

    def _coerce_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]
