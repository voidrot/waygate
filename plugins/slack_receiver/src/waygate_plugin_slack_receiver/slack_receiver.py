import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, List
from uuid import uuid4

from waygate_core.plugin_base import IngestionPlugin
from waygate_core.schemas import RawDocument
from waygate_plugin_slack_receiver.metadata import SlackSourceMetadata


class SlackReceiver(IngestionPlugin):
    @property
    def plugin_name(self) -> str:
        return "slack_receiver"

    def poll(self, since_timestamp=None) -> List[RawDocument]:
        export_path = os.getenv("SLACK_EXPORT_PATH")
        if not export_path:
            return []

        root = Path(export_path)
        if not root.exists():
            return []

        documents: list[RawDocument] = []
        for export_file in sorted(root.glob("*.json")):
            mtime = datetime.fromtimestamp(export_file.stat().st_mtime, tz=UTC)
            if since_timestamp and mtime <= since_timestamp:
                continue

            try:
                payload = json.loads(export_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            messages = payload.get("messages") if isinstance(payload, dict) else None
            if isinstance(messages, list):
                for message in messages:
                    if isinstance(message, dict):
                        docs = self._normalize_payload(
                            {
                                "event_id": message.get("event_id") or str(uuid4()),
                                "event": {
                                    **message,
                                    "channel": message.get("channel")
                                    or payload.get("channel")
                                    or payload.get("channel_id"),
                                },
                            }
                        )
                        documents.extend(docs)
            elif isinstance(payload, dict):
                documents.extend(self._normalize_payload(payload))

        return documents

    def handle_webhook(self, payload: dict) -> List[RawDocument]:
        if not payload:
            raise ValueError("Webhook body cannot be empty")

        return self._normalize_payload(payload)

    def _normalize_payload(self, payload: dict) -> List[RawDocument]:
        if not payload:
            return []

        raw_event = payload.get("event")
        event: dict[str, Any] = raw_event if isinstance(raw_event, dict) else payload

        channel_id = self._string(event, "channel") or self._string(
            payload, "channel_id"
        )
        thread_ts = self._string(event, "thread_ts") or self._string(
            payload, "thread_ts"
        )
        anchor_id = self._string(event, "ts") or self._string(payload, "ts")
        user_id = self._string(event, "user") or self._string(payload, "user_id")
        semantic_type = self._string(event, "type") or self._string(payload, "type")

        source_id = self._string(payload, "event_id") or anchor_id or str(uuid4())
        source_url = self._string(event, "permalink") or self._string(
            payload, "permalink"
        )

        text = self._string(event, "text") or self._string(payload, "text")
        content = text or json.dumps(event, sort_keys=True)
        timestamp = self._timestamp_from_payload(event=event, payload=payload)

        tags = ["slack"]
        if semantic_type:
            tags.append(semantic_type)
        if channel_id:
            tags.append(channel_id)

        participants = [user_id] if user_id else []
        metadata = SlackSourceMetadata(
            channel_id=channel_id,
            thread_ts=thread_ts,
            participants=participants,
            semantic_type=semantic_type,
            anchor_id=anchor_id,
        )

        return [
            RawDocument(
                source_type="slack",
                source_id=source_id,
                timestamp=timestamp,
                content=content,
                tags=tags,
                source_url=source_url,
                source_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                source_metadata=metadata,
            )
        ]

    def _timestamp_from_payload(
        self, *, event: dict[str, Any], payload: dict[str, Any]
    ) -> datetime:
        timestamp_value = self._string(event, "ts") or self._string(payload, "ts")
        if timestamp_value is None:
            return datetime.now(UTC)

        try:
            return datetime.fromtimestamp(float(timestamp_value), tz=UTC)
        except (TypeError, ValueError):
            try:
                parsed = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
            except (TypeError, ValueError):
                return datetime.now(UTC)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed

    def _string(self, payload: dict[str, Any], *keys: str) -> str | None:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        if current is None:
            return None
        return str(current)

    async def listen(
        self, on_data_callback: Callable[[List[RawDocument]], Awaitable[None]]
    ) -> None:
        events = getattr(self, "_listen_events", None)

        if events is None:
            fixture_path = os.getenv("SLACK_STREAM_FIXTURE")
            if fixture_path:
                try:
                    loaded = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    loaded = []
                if isinstance(loaded, list):
                    events = loaded

        if not isinstance(events, list):
            return

        for payload in events:
            if not isinstance(payload, dict):
                continue
            docs = self._normalize_payload(payload)
            if docs:
                await on_data_callback(docs)
