from compiler.nodes import human_review
from compiler.human_review_flow import read_human_review_record
from compiler.state import GraphState
from waygate_core.schemas import AuditEventType


class _FakeStorage:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.audit_events = []
        self.meta_documents: dict[str, str] = {}

    def write_staging_document(self, document_id: str, content: str) -> str:
        self.calls.append((document_id, content))
        return f"file:///tmp/staging/{document_id}.md"

    def write_meta_document(
        self, namespace: str, document_id: str, content: str
    ) -> str:
        uri = f"meta/{namespace}/{document_id}"
        self.meta_documents[uri] = content
        return uri

    def read_meta_document(self, uri: str) -> str:
        return self.meta_documents[uri]

    def write_audit_event(self, event) -> str:
        self.audit_events.append(event)
        return f"meta/audit/{event.event_id}"


def test_human_review_node_writes_staging_artifact(monkeypatch) -> None:
    fake_storage = _FakeStorage()
    monkeypatch.setattr(human_review, "storage", fake_storage)

    state: GraphState = {
        "state_version": "1",
        "trace_id": "trace-123",
        "enqueued_at": "2026-04-06T12:00:00+00:00",
        "target_topic": "Receiver Reliability",
        "current_draft": "Draft body",
        "qa_feedback": "Missing citations",
        "staging_uri": None,
        "revision_count": 3,
        "status": "rejected",
        "new_document_uris": ["file:///tmp/raw/1.md"],
        "raw_documents_metadata": [],
    }

    result = human_review.human_review_node(state)

    assert result["status"] == "awaiting_human_review"
    assert result["staging_uri"].startswith("file:///tmp/staging/")
    assert result["human_review_uri"].startswith("meta/human-review/")
    assert len(fake_storage.calls) == 1

    document_id, content = fake_storage.calls[0]
    assert "receiver-reliability" in document_id
    assert "Escalation Context" in content
    assert "trace-123" in content
    assert "Missing citations" in content
    assert "Draft body" in content
    assert len(fake_storage.audit_events) == 1
    event = fake_storage.audit_events[0]
    assert event.event_type == AuditEventType.COMPILER_HUMAN_REVIEW_ESCALATED
    assert event.trace_id == "trace-123"
    assert event.payload["revision_count"] == 3
    assert event.payload["human_review_uri"] == result["human_review_uri"]

    review_record = read_human_review_record(result["human_review_uri"])
    assert review_record.status == "pending"
    assert review_record.staging_uri == result["staging_uri"]
    assert review_record.trace_id == "trace-123"
