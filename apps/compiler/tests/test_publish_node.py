from datetime import datetime, timezone
from typing import Any, cast

import frontmatter

from compiler.nodes import publish
from compiler.state import GraphState
from waygate_core.schemas import RawDocument


class _FakeStorage:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str]] = []

    def write_live_document(self, filename: str, content: str) -> None:
        self.writes.append((filename, content))


def _raw_doc(*, source_id: str, source_url: str | None, tags: list[str]) -> dict:
    return RawDocument.model_validate(
        {
            "source_type": "github",
            "source_id": source_id,
            "timestamp": datetime(2026, 4, 6, 12, 0, tzinfo=timezone.utc),
            "content": "payload",
            "source_url": source_url,
            "tags": tags,
        }
    ).model_dump(mode="json")


def test_publish_node_writes_canonical_frontmatter_with_promoted_fields(
    monkeypatch,
) -> None:
    fake_storage = _FakeStorage()
    monkeypatch.setattr(publish, "storage", fake_storage)

    state: GraphState = {
        "target_topic": "Webhook Metadata Promotion",
        "current_draft": "This is the compiled draft.",
        "qa_feedback": None,
        "revision_count": 0,
        "status": "drafting",
        "new_document_uris": ["file:///tmp/raw/fallback-a.md"],
        "raw_documents_metadata": [
            _raw_doc(
                source_id="issue-1",
                source_url="https://github.com/voidrot/waygate/issues/1",
                tags=["github", "issue"],
            ),
            _raw_doc(
                source_id="pr-2",
                source_url="https://github.com/voidrot/waygate/pull/2",
                tags=["github", "review"],
            ),
        ],
    }

    result = publish.publish_node(state)

    assert result == {"status": "completed"}
    assert len(fake_storage.writes) == 1

    filename, body = fake_storage.writes[0]
    assert filename == "webhook-metadata-promotion.md"

    post = frontmatter.loads(body)
    metadata = cast(dict[str, Any], post.metadata)
    assert metadata["source_type"] == "synthesis"
    assert metadata["status"] == "live"
    assert metadata["visibility"] == "internal"
    assert metadata["lineage"]
    assert len(cast(list[str], metadata["lineage"])) == 2
    assert metadata["sources"] == [
        "https://github.com/voidrot/waygate/issues/1",
        "https://github.com/voidrot/waygate/pull/2",
    ]
    assert metadata["tags"] == ["github", "issue", "review"]
    assert post.content == "This is the compiled draft."


def test_publish_node_falls_back_to_raw_uris_when_source_urls_missing(
    monkeypatch,
) -> None:
    fake_storage = _FakeStorage()
    monkeypatch.setattr(publish, "storage", fake_storage)

    state: GraphState = {
        "target_topic": "Fallback Sources",
        "current_draft": "Body",
        "qa_feedback": None,
        "revision_count": 0,
        "status": "drafting",
        "new_document_uris": [
            "file:///tmp/raw/doc-a.md",
            "file:///tmp/raw/doc-b.md",
        ],
        "raw_documents_metadata": [
            _raw_doc(source_id="a", source_url=None, tags=["a"]),
            _raw_doc(source_id="b", source_url=None, tags=["b"]),
        ],
    }

    publish.publish_node(state)

    _, body = fake_storage.writes[0]
    post = frontmatter.loads(body)
    metadata = cast(dict[str, Any], post.metadata)
    assert metadata["sources"] == [
        "file:///tmp/raw/doc-a.md",
        "file:///tmp/raw/doc-b.md",
    ]
