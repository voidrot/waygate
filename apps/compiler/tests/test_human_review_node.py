from compiler.nodes import human_review
from compiler.state import GraphState


class _FakeStorage:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def write_staging_document(self, document_id: str, content: str) -> str:
        self.calls.append((document_id, content))
        return f"file:///tmp/staging/{document_id}.md"


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

    assert result["status"] == "escalated"
    assert result["staging_uri"].startswith("file:///tmp/staging/")
    assert len(fake_storage.calls) == 1

    document_id, content = fake_storage.calls[0]
    assert "receiver-reliability" in document_id
    assert "Escalation Context" in content
    assert "trace-123" in content
    assert "Missing citations" in content
    assert "Draft body" in content
