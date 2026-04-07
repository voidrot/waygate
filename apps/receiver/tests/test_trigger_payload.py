from datetime import datetime, timezone
from uuid import UUID

from receiver.services.trigger import _build_initial_state
from waygate_core.plugin_base import RawDocument


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
    assert state["template_name"] == "default"
    assert state["status"] == "pending_draft"
    assert state["new_document_uris"] == ["file:///tmp/raw.md"]
    assert state["revision_count"] == 0
    assert state["raw_documents_metadata"][0]["source_id"] == "issue/1"
    assert state["current_draft"] is None
    assert state["qa_feedback"] is None
    assert state["staging_uri"] is None

    UUID(state["trace_id"])
    datetime.fromisoformat(state["enqueued_at"])
