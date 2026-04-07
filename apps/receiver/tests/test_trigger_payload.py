from datetime import datetime, timezone
from uuid import UUID

import pytest

from receiver.services import trigger
from receiver.services.trigger import _build_initial_state
from waygate_core.plugin_base import RawDocument
from waygate_core.schemas import AuditEventType


def test_build_initial_state_includes_traceability_fields() -> None:
    documents = [
        RawDocument(
            source_type="github",
            source_id="issue/1",
            timestamp=datetime(2026, 4, 6, tzinfo=timezone.utc),
            content="hello",
            tags=["a"],
        )
    ]

    state = _build_initial_state(documents, ["file:///tmp/raw.md"])

    assert state["state_version"] == "1"
    assert state["target_topic"] == "Github issue 1"
    assert state["document_type"] == "concepts"
    assert state["status"] == "pending_draft"
    assert state["new_document_uris"] == ["file:///tmp/raw.md"]
    assert state["revision_count"] == 0
    assert state["raw_documents_metadata"][0]["source_id"] == "issue/1"
    assert state["current_draft"] is None
    assert state["qa_feedback"] is None
    assert state["staging_uri"] is None

    UUID(state["trace_id"])
    datetime.fromisoformat(state["enqueued_at"])


class _FakeStorage:
    def __init__(self) -> None:
        self.saved_documents: list[RawDocument] = []
        self.audit_events = []

    def write_raw_documents(self, documents: list[RawDocument]) -> list[str]:
        self.saved_documents.extend(documents)
        return [f"file:///tmp/raw/{document.doc_id}.md" for document in documents]

    def write_audit_event(self, event) -> str:
        self.audit_events.append(event)
        return f"meta/audit/{event.event_id}"


class _FakeJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id


class _FakeQueue:
    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return _FakeJob("job-123")


@pytest.mark.anyio
async def test_save_and_trigger_langgraph_writes_audit_event(monkeypatch) -> None:
    fake_storage = _FakeStorage()
    fake_queue = _FakeQueue()
    monkeypatch.setattr(trigger, "storage", fake_storage)
    monkeypatch.setattr(trigger, "draft_queue", fake_queue)

    documents = [
        RawDocument(
            source_type="github",
            source_id="issue/1",
            timestamp=datetime(2026, 4, 6, tzinfo=timezone.utc),
            content="hello",
            tags=["a"],
        )
    ]

    await trigger.save_and_trigger_langgraph_async(documents)

    assert len(fake_queue.calls) == 1
    assert len(fake_storage.audit_events) == 1
    event = fake_storage.audit_events[0]
    assert event.event_type == AuditEventType.RECEIVER_ENQUEUED
    assert event.document_ids == [documents[0].doc_id]
    assert event.payload["job_id"] == "job-123"
    assert event.payload["document_count"] == 1
    UUID(event.trace_id)
