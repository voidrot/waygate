from compiler import middleware
from compiler.state import GraphState


def test_apply_hooks_runs_pre_and_post_in_order() -> None:
    middleware.clear_hooks()
    observed: list[str] = []
    initial_state: GraphState = {
        "state_version": "1",
        "trace_id": "trace",
        "enqueued_at": "2026-04-06T00:00:00+00:00",
        "new_document_uris": [],
        "raw_documents_metadata": [],
        "target_topic": "topic",
        "current_draft": None,
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "pending",
    }

    def pre_one(node_name, state: GraphState) -> GraphState:
        observed.append(f"pre1:{node_name}")
        return {**state, "status": "pre_one"}

    def pre_two(node_name, state: GraphState) -> GraphState:
        observed.append(f"pre2:{node_name}")
        return {**state, "status": "pre_two"}

    def post_one(node_name, state, result):
        observed.append(f"post1:{node_name}:{state['status']}")
        new_result = dict(result)
        new_result["post"] = "one"
        return new_result

    def post_two(node_name, state, result):
        observed.append(f"post2:{node_name}:{result['post']}")
        new_result = dict(result)
        new_result["post"] = "two"
        return new_result

    def node(state):
        observed.append(f"node:{state['status']}")
        return {"status": "ok"}

    middleware.register_pre_hook(pre_one)
    middleware.register_pre_hook(pre_two)
    middleware.register_post_hook(post_one)
    middleware.register_post_hook(post_two)

    wrapped = middleware.apply_hooks("draft", node)
    result = wrapped(initial_state)

    assert result["post"] == "two"
    assert observed == [
        "pre1:draft",
        "pre2:draft",
        "node:pre_two",
        "post1:draft:pre_two",
        "post2:draft:one",
    ]

    middleware.clear_hooks()
