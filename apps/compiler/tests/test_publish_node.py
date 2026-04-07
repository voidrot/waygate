from datetime import datetime, timezone
from typing import Any, cast

import frontmatter

from compiler.nodes import publish
from compiler.state import GraphState
from waygate_core.schemas import AuditEventType, RawDocument


class _FakeStorage:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str, str]] = []
        self.audit_events = []

    def write_live_document_to_category(
        self, filename: str, content: str, category: str
    ) -> str:
        self.writes.append((filename, content, category))
        return f"file:///tmp/live/{category}/{filename}.md"

    def write_audit_event(self, event) -> str:
        self.audit_events.append(event)
        return f"meta/audit/{event.event_id}"


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
        "state_version": "1",
        "trace_id": "trace-1",
        "enqueued_at": "2026-04-06T11:59:59+00:00",
        "target_topic": "Webhook Metadata Promotion",
        "current_draft": "This is the compiled draft.",
        "qa_feedback": None,
        "staging_uri": None,
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

    filename, body, category = fake_storage.writes[0]
    assert filename.startswith("webhook-metadata-promotion-")
    assert category == "concepts"

    post = frontmatter.loads(body)
    metadata = cast(dict[str, Any], post.metadata)
    assert metadata["document_type"] == "concepts"
    assert metadata["source_type"] == "synthesis"
    assert metadata["source_hash"]
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
    assert len(fake_storage.audit_events) == 1
    event = fake_storage.audit_events[0]
    assert event.event_type == AuditEventType.COMPILER_PUBLISH_COMPLETED
    assert event.trace_id == "trace-1"
    assert event.payload["document_type"] == "concepts"


def test_publish_node_falls_back_to_raw_uris_when_source_urls_missing(
    monkeypatch,
) -> None:
    fake_storage = _FakeStorage()
    monkeypatch.setattr(publish, "storage", fake_storage)

    state: GraphState = {
        "state_version": "1",
        "trace_id": "trace-2",
        "enqueued_at": "2026-04-06T11:59:59+00:00",
        "target_topic": "Fallback Sources",
        "current_draft": "Body",
        "qa_feedback": None,
        "staging_uri": None,
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

    _, body, category = fake_storage.writes[0]
    post = frontmatter.loads(body)
    metadata = cast(dict[str, Any], post.metadata)
    assert category == "concepts"
    assert metadata["sources"] == [
        "file:///tmp/raw/doc-a.md",
        "file:///tmp/raw/doc-b.md",
    ]


# ---------------------------------------------------------------
# NEW: Naming stability and collision resistance tests
# ---------------------------------------------------------------


def test_publish_node_generates_collision_resistant_filenames(monkeypatch) -> None:
    """Verify that different topics produce different filenames."""
    fake_storage = _FakeStorage()
    monkeypatch.setattr(publish, "storage", fake_storage)

    # First document
    state1: GraphState = {
        "state_version": "1",
        "trace_id": "trace-1a",
        "enqueued_at": "2026-04-06T11:59:59+00:00",
        "target_topic": "Topic A",
        "current_draft": "# Topic A\nBody A",
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "drafting",
        "new_document_uris": ["uri-1"],
        "raw_documents_metadata": [_raw_doc(source_id="s1", source_url=None, tags=[])],
    }

    publish.publish_node(state1)
    filename1 = fake_storage.writes[0][0]

    # Second document with different topic
    fake_storage.writes.clear()
    state2: GraphState = {
        "state_version": "1",
        "trace_id": "trace-1b",
        "enqueued_at": "2026-04-06T12:00:00+00:00",
        "target_topic": "Topic B",
        "current_draft": "# Topic B\nBody B",
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "drafting",
        "new_document_uris": ["uri-2"],
        "raw_documents_metadata": [_raw_doc(source_id="s2", source_url=None, tags=[])],
    }

    publish.publish_node(state2)
    filename2 = fake_storage.writes[0][0]

    # Different topics should produce different filenames
    assert filename1 != filename2
    assert "topic-a" in filename1
    assert "topic-b" in filename2


def test_publish_node_filename_stability_with_same_content(monkeypatch) -> None:
    """Verify that publishing the same topic produces consistent filename prefixes."""
    fake_storage = _FakeStorage()
    monkeypatch.setattr(publish, "storage", fake_storage)

    # First publish
    state1: GraphState = {
        "state_version": "1",
        "trace_id": "trace-2a",
        "enqueued_at": "2026-04-06T11:59:59+00:00",
        "target_topic": "Architecture Design",
        "current_draft": "# Architecture Design\nVersion 1",
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "drafting",
        "new_document_uris": ["uri-a"],
        "raw_documents_metadata": [_raw_doc(source_id="sa", source_url=None, tags=[])],
    }

    publish.publish_node(state1)
    filename1 = fake_storage.writes[0][0]

    # Second publish of same topic but different content
    fake_storage.writes.clear()
    state2: GraphState = {
        "state_version": "1",
        "trace_id": "trace-2b",
        "enqueued_at": "2026-04-06T12:00:00+00:00",
        "target_topic": "Architecture Design",
        "current_draft": "# Architecture Design\nVersion 2",
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "drafting",
        "new_document_uris": ["uri-b"],
        "raw_documents_metadata": [_raw_doc(source_id="sb", source_url=None, tags=[])],
    }

    publish.publish_node(state2)
    filename2 = fake_storage.writes[0][0]

    # Both should start with the same slug (storage receives names without .md extension)
    assert filename1.startswith("architecture-design-")
    assert filename2.startswith("architecture-design-")
    # Storage receives names without .md, confirmed by publish node's file_name[:-3] call
    assert not filename1.endswith(".md")
    assert not filename2.endswith(".md")


def test_publish_node_preserves_document_type_in_category(monkeypatch) -> None:
    """Verify document_type field is used to select the output category."""
    fake_storage = _FakeStorage()
    monkeypatch.setattr(publish, "storage", fake_storage)

    state: GraphState = {
        "state_version": "1",
        "trace_id": "trace-3",
        "enqueued_at": "2026-04-06T11:59:59+00:00",
        "target_topic": "Entity Profiles",
        "current_draft": "# Entity Profiles\nContent",
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "drafting",
        "new_document_uris": ["uri"],
        "raw_documents_metadata": [_raw_doc(source_id="s", source_url=None, tags=[])],
        "document_type": "entities",
    }

    publish.publish_node(state)

    _, _, category = fake_storage.writes[0]
    assert category == "entities"
