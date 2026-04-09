from compiler import human_review_flow
from compiler.human_review_flow import (
    HumanReviewDecision,
    HumanReviewStatus,
)
from compiler.state import GraphState
from waygate_core.schemas import AuditEventType


class _FakeStorage:
    def __init__(self) -> None:
        self.meta_documents: dict[str, str] = {}
        self.audit_events = []

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


def _base_state() -> GraphState:
    return {
        "state_version": "1",
        "trace_id": "trace-review-1",
        "enqueued_at": "2026-04-06T00:00:00+00:00",
        "new_document_uris": ["file:///tmp/raw.md"],
        "raw_documents_metadata": [],
        "target_topic": "Topic",
        "current_draft": "Draft body",
        "qa_feedback": "Old feedback",
        "staging_uri": None,
        "revision_count": 3,
        "status": "awaiting_human_review",
    }


def test_resume_human_review_revise_reenters_graph(monkeypatch) -> None:
    fake_storage = _FakeStorage()
    monkeypatch.setattr(human_review_flow, "storage", fake_storage)

    record, review_uri = human_review_flow.create_human_review_record(
        _base_state(),
        "file:///tmp/staging/review.md",
    )
    assert record.status == HumanReviewStatus.PENDING

    recorded = human_review_flow.submit_human_review_feedback(
        review_uri,
        decision=HumanReviewDecision.REVISE,
        feedback="Add citations",
    )
    assert recorded.status == HumanReviewStatus.FEEDBACK_RECORDED

    captured = {}

    class _Workflow:
        def invoke(self, state):
            captured.update(state)
            return {**state, "status": "completed"}

    monkeypatch.setattr(human_review_flow, "_build_workflow_app", lambda: _Workflow())

    result = human_review_flow.resume_human_review(review_uri)

    assert captured["qa_feedback"] == "Add citations"
    assert captured["revision_count"] == 0
    assert captured["status"] == "pending_draft"
    assert captured["human_review_uri"] == review_uri
    assert result["status"] == "completed"

    updated = human_review_flow.read_human_review_record(review_uri)
    assert updated.status == HumanReviewStatus.RESUMED
    assert updated.payload["final_status"] == "completed"
    assert [event.event_type for event in fake_storage.audit_events] == [
        AuditEventType.COMPILER_HUMAN_REVIEW_FEEDBACK_RECORDED,
        AuditEventType.COMPILER_HUMAN_REVIEW_RESUMED,
    ]


def test_resume_human_review_approve_publishes_draft(monkeypatch) -> None:
    fake_storage = _FakeStorage()
    monkeypatch.setattr(human_review_flow, "storage", fake_storage)

    _, review_uri = human_review_flow.create_human_review_record(
        _base_state(),
        "file:///tmp/staging/review.md",
    )
    human_review_flow.submit_human_review_feedback(
        review_uri,
        decision=HumanReviewDecision.APPROVE,
        feedback="Approved",
        revised_draft="# Final\n\nEdited by human",
    )

    captured = {}

    def _fake_publish(state):
        captured.update(state)
        return {"status": "completed"}

    monkeypatch.setattr(human_review_flow, "_publish_reviewed_draft", _fake_publish)

    result = human_review_flow.resume_human_review(review_uri)

    assert captured["current_draft"] == "# Final\n\nEdited by human"
    assert captured["human_review_uri"] == review_uri
    assert result["status"] == "completed"


def test_resume_human_review_reject_closes_record(monkeypatch) -> None:
    fake_storage = _FakeStorage()
    monkeypatch.setattr(human_review_flow, "storage", fake_storage)

    _, review_uri = human_review_flow.create_human_review_record(
        _base_state(),
        "file:///tmp/staging/review.md",
    )
    human_review_flow.submit_human_review_feedback(
        review_uri,
        decision=HumanReviewDecision.REJECT,
        feedback="Out of scope",
    )

    result = human_review_flow.resume_human_review(review_uri)

    assert result["status"] == "human_rejected"
    updated = human_review_flow.read_human_review_record(review_uri)
    assert updated.status == HumanReviewStatus.CLOSED
