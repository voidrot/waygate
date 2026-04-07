import json
from datetime import UTC, datetime

import pytest

from waygate_plugin_linkwarden_receiver.metadata import LinkwardenSourceMetadata
from waygate_plugin_linkwarden_receiver.webhook_receiver import LinkwardenReceiver


class _MockResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_poll_populates_web_metadata_for_linkwarden(monkeypatch) -> None:
    receiver = LinkwardenReceiver()

    monkeypatch.setenv("LINKWARDEN_BASE_URL", "https://example.linkwarden")
    monkeypatch.setenv("LINKWARDEN_TOKEN", "token")

    page = {
        "data": {
            "links": [
                {
                    "id": 42,
                    "url": "https://example.com/blog/post",
                    "name": "Test link",
                    "description": "hello world",
                    "tags": [{"name": "research"}, {"name": "gar"}],
                    "updatedAt": "2026-04-06T10:00:00Z",
                    "createdBy": "Buck",
                }
            ],
            "nextCursor": None,
        }
    }

    monkeypatch.setattr(
        "waygate_plugin_linkwarden_receiver.webhook_receiver.urlopen",
        lambda _req: _MockResponse(page),
    )

    docs = receiver.poll()

    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_type == "web"
    assert doc.source_id == "42"
    assert doc.source_url == "https://example.com/blog/post"
    assert doc.source_hash
    assert doc.doc_id
    assert doc.tags == ["research", "gar"]
    assert doc.source_metadata is not None
    assert isinstance(doc.source_metadata, LinkwardenSourceMetadata)
    assert doc.source_metadata.kind == "web"
    assert doc.source_metadata.domain == "example.com"
    assert doc.source_metadata.keywords == ["research", "gar"]


def test_poll_handles_pagination_and_since_timestamp(monkeypatch) -> None:
    receiver = LinkwardenReceiver()
    monkeypatch.setenv("LINKWARDEN_BASE_URL", "https://example.linkwarden")
    monkeypatch.setenv("LINKWARDEN_TOKEN", "token")

    pages = iter(
        [
            {
                "data": {
                    "links": [
                        {
                            "id": 2,
                            "url": "https://example.com/b",
                            "name": "B",
                            "updatedAt": "2026-04-06T12:00:00Z",
                            "tags": [],
                        }
                    ],
                    "nextCursor": 2,
                }
            },
            {
                "data": {
                    "links": [
                        {
                            "id": 1,
                            "url": "https://example.com/a",
                            "name": "A",
                            "updatedAt": "2026-04-06T09:00:00Z",
                            "tags": [],
                        }
                    ],
                    "nextCursor": None,
                }
            },
        ]
    )

    monkeypatch.setattr(
        "waygate_plugin_linkwarden_receiver.webhook_receiver.urlopen",
        lambda _req: _MockResponse(next(pages)),
    )

    docs = receiver.poll(since_timestamp=datetime(2026, 4, 6, 10, tzinfo=UTC))

    assert [doc.source_id for doc in docs] == ["2"]


def test_handle_webhook_is_not_supported() -> None:
    receiver = LinkwardenReceiver()

    with pytest.raises(NotImplementedError):
        receiver.handle_webhook({"id": 1})
