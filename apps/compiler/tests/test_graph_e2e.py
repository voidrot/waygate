from compiler import graph, middleware
from compiler.state import GraphState


def _base_state() -> GraphState:
    return {
        "state_version": "1",
        "trace_id": "trace-1",
        "enqueued_at": "2026-04-06T00:00:00+00:00",
        "new_document_uris": ["file:///tmp/raw.md"],
        "raw_documents_metadata": [],
        "target_topic": "Topic",
        "current_draft": None,
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "pending_draft",
    }


def test_graph_happy_path_with_rejection_retry(monkeypatch) -> None:
    middleware.clear_hooks()

    calls = {"draft": 0, "review": 0, "publish": 0}

    def fake_draft(state: GraphState) -> dict:
        calls["draft"] += 1
        return {
            "current_draft": f"draft-{calls['draft']}",
            "revision_count": state["revision_count"] + 1,
            "status": "reviewing",
        }

    def fake_review(state: GraphState) -> dict:
        calls["review"] += 1
        if state["revision_count"] >= 2:
            return {"status": "approved", "qa_feedback": ""}
        return {"status": "rejected", "qa_feedback": "needs edits"}

    def fake_publish(_state: GraphState) -> dict:
        calls["publish"] += 1
        return {"status": "completed"}

    monkeypatch.setattr(graph, "draft_node", fake_draft)
    monkeypatch.setattr(graph, "review_node", fake_review)
    monkeypatch.setattr(graph, "publish_node", fake_publish)

    app = graph.build_graph()
    final_state = app.invoke(_base_state())

    assert final_state["status"] == "completed"
    assert calls == {"draft": 2, "review": 2, "publish": 1}


def test_graph_escalates_after_three_rejections(monkeypatch) -> None:
    middleware.clear_hooks()

    calls = {"draft": 0, "review": 0, "human_review": 0}

    def fake_draft(state: GraphState) -> dict:
        calls["draft"] += 1
        return {
            "current_draft": f"draft-{calls['draft']}",
            "revision_count": state["revision_count"] + 1,
            "status": "reviewing",
        }

    def fake_review(_state: GraphState) -> dict:
        calls["review"] += 1
        return {"status": "rejected", "qa_feedback": "still bad"}

    def fake_human_review(_state: GraphState) -> dict:
        calls["human_review"] += 1
        return {
            "status": "escalated",
            "staging_uri": "file:///tmp/staging/escalated.md",
        }

    monkeypatch.setattr(graph, "draft_node", fake_draft)
    monkeypatch.setattr(graph, "review_node", fake_review)
    monkeypatch.setattr(graph, "human_review_node", fake_human_review)

    app = graph.build_graph()
    final_state = app.invoke(_base_state())

    assert final_state["status"] == "escalated"
    assert final_state["staging_uri"].startswith("file:///tmp/staging/")
    assert calls == {"draft": 3, "review": 3, "human_review": 1}
