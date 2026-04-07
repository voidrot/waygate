from compiler.nodes import draft
from compiler.state import GraphState


class _FakeStorage:
    def read_raw_document(self, uri: str) -> str:
        return f"raw content from {uri}"


class _FakeLLM:
    def __init__(self) -> None:
        self.messages = None

    def invoke(self, messages):
        self.messages = messages

        class _Response:
            content = "# Generated Title\n\nBody"

        return _Response()


def test_draft_node_includes_template_scaffold(monkeypatch) -> None:
    fake_storage = _FakeStorage()
    fake_llm = _FakeLLM()

    monkeypatch.setattr(draft, "storage", fake_storage)
    monkeypatch.setattr(draft, "get_llm", lambda *_args: fake_llm)

    state: GraphState = {
        "state_version": "1",
        "trace_id": "trace-1",
        "enqueued_at": "2026-04-06T00:00:00+00:00",
        "new_document_uris": ["file:///tmp/raw.md"],
        "raw_documents_metadata": [],
        "target_topic": "WayGate Contract",
        "document_type": "concepts",
        "current_draft": None,
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "pending_draft",
    }

    result = draft.draft_node(state)

    assert result["status"] == "reviewing"
    assert fake_llm.messages is not None
    assert "TEMPLATE SCAFFOLD:" in fake_llm.messages[0].content
    assert "## Summary" in fake_llm.messages[0].content
