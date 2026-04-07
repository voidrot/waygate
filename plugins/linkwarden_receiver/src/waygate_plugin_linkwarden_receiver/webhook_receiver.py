import hashlib
import json
import os
from datetime import UTC, datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from waygate_core.plugin_base import IngestionPlugin
from waygate_core.schemas import RawDocument

from .metadata import LinkwardenSourceMetadata


class LinkwardenReceiver(IngestionPlugin):
    @property
    def plugin_name(self) -> str:
        return "linkwarden_receiver"

    def poll(self, since_timestamp=None) -> list[RawDocument]:
        base_url = os.getenv("LINKWARDEN_BASE_URL")
        token = os.getenv("LINKWARDEN_TOKEN")
        if not base_url or not token:
            return []

        cursor: int | None = None
        documents: list[RawDocument] = []
        while True:
            response = self._request_search_page(
                base_url=base_url,
                token=token,
                cursor=cursor,
            )
            page_items, cursor = self._extract_page_data(response)
            if not page_items:
                break

            for item in page_items:
                if not isinstance(item, dict):
                    continue
                document = self._build_document(item, defaults={}, index=0)
                if since_timestamp and document.timestamp <= since_timestamp:
                    continue
                documents.append(document)

            if cursor is None:
                break

        return documents

    def handle_webhook(self, payload: dict) -> list[RawDocument]:
        raise NotImplementedError("Linkwarden receiver only supports poll mode")

    def _request_search_page(
        self,
        *,
        base_url: str,
        token: str,
        cursor: int | None,
    ) -> dict[str, Any]:
        query: dict[str, str] = {"sort": os.getenv("LINKWARDEN_SORT", "0")}
        search_query = os.getenv("LINKWARDEN_SEARCH_QUERY")
        if search_query:
            query["searchQueryString"] = search_query
        collection_id = os.getenv("LINKWARDEN_COLLECTION_ID")
        if collection_id:
            query["collectionId"] = collection_id
        tag_id = os.getenv("LINKWARDEN_TAG_ID")
        if tag_id:
            query["tagId"] = tag_id
        pinned_only = os.getenv("LINKWARDEN_PINNED_ONLY")
        if pinned_only:
            query["pinnedOnly"] = pinned_only
        if cursor is not None:
            query["cursor"] = str(cursor)

        api_base = base_url.rstrip("/")
        url = f"{api_base}/api/v1/search?{urlencode(query)}"
        request = Request(
            url=url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="GET",
        )
        with urlopen(request) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else {}

    def _extract_page_data(
        self, payload: dict[str, Any]
    ) -> tuple[list[Any], int | None]:
        data = payload.get("data")
        if isinstance(data, dict):
            links = data.get("links")
            next_cursor = data.get("nextCursor")
            if isinstance(links, list):
                parsed_cursor = self._coerce_cursor(next_cursor)
                return links, parsed_cursor

        # Backward-compatible fallback if the API shape changes.
        response = payload.get("response")
        if isinstance(response, list):
            return response, None

        return [], None

    def _coerce_cursor(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except TypeError, ValueError:
            return None

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
            source_type="web",
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
    ) -> LinkwardenSourceMetadata:
        merged = {**defaults, **payload}
        source_url = self._resolve_source_url(payload, defaults)
        domain = self._first_string(merged, "domain")
        if domain is None and source_url:
            domain = urlparse(source_url).netloc or None

        return LinkwardenSourceMetadata(
            author=self._first_string(merged, "author", "createdBy", "created_by"),
            clipped_at=self._first_string(
                merged, "clipped_at", "createdAt", "created_at"
            ),
            domain=domain,
            local_assets=self._coerce_list(merged.get("local_assets")),
            keywords=self._resolve_keywords(merged),
            linkwarden_id=self._first_string(merged, "linkwarden_id", "id"),
            collection_id=self._first_string(merged, "collection_id", "collectionId")
            or self._nested_string(merged, "collection", "id"),
        )

    def _resolve_keywords(self, payload: dict[str, Any]) -> list[str]:
        tags = payload.get("tags")
        if isinstance(tags, list):
            keywords: list[str] = []
            for tag in tags:
                if isinstance(tag, dict):
                    name = tag.get("name")
                    if name is not None:
                        keywords.append(str(name))
                else:
                    keywords.append(str(tag))
            return keywords
        if isinstance(tags, str):
            split_tags = [tag.strip() for tag in tags.split(",")]
            return [tag for tag in split_tags if tag]
        return self._coerce_list(payload.get("keywords"))

    def _resolve_source_id(
        self, payload: dict[str, Any], defaults: dict[str, Any], index: int
    ) -> str:
        source_id = self._first_string(
            payload,
            "source_id",
            "id",
            "linkwarden_id",
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
            "linkwarden_id",
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
            "updatedAt",
            "timestamp",
            "created_at",
            "createdAt",
            "importDate",
            "occurred_at",
            "event_time",
            "time",
        )
        if timestamp_value is None:
            timestamp_value = self._first_value(
                defaults,
                "updatedAt",
                "timestamp",
                "created_at",
                "createdAt",
                "importDate",
                "occurred_at",
                "event_time",
                "time",
            )

        if isinstance(timestamp_value, datetime):
            timestamp = timestamp_value
        elif isinstance(timestamp_value, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp_value, tz=UTC)
        elif isinstance(timestamp_value, str):
            try:
                timestamp = datetime.fromisoformat(
                    timestamp_value.replace("Z", "+00:00")
                )
            except ValueError:
                timestamp = datetime.now(UTC)
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
            split_tags = [tag.strip() for tag in tag_value.split(",")]
            return [tag for tag in split_tags if tag]
        if isinstance(tag_value, list):
            tags: list[str] = []
            for tag in tag_value:
                if isinstance(tag, dict):
                    name = tag.get("name")
                    if name is not None:
                        tags.append(str(name))
                else:
                    tags.append(str(tag))
            return tags
        return [str(tag_value)]

    def _resolve_content(self, payload: dict[str, Any]) -> str:
        for key in (
            "content",
            "body",
            "text",
            "message",
            "description",
            "notes",
            "textContent",
        ):
            value = payload.get(key)
            if value is None:
                continue
            self._ensure_value_present(value)
            if isinstance(value, str):
                return value
            return json.dumps(value, sort_keys=True)

        title = self._first_string(payload, "title")
        url = self._first_string(payload, "url", "link")
        if title and url:
            return f"{title}\n{url}"
        if title:
            return title
        if url:
            return url
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

    def _nested_string(self, payload: dict[str, Any], *keys: str) -> str | None:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        if current is None:
            return None
        return str(current)

    def _coerce_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]
