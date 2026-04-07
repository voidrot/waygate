from compiler.nodes.draft import draft_node
from compiler.nodes.human_review import human_review_node
from compiler.nodes.publish import publish_node
from compiler.nodes.review import review_node
from compiler.middleware import apply_hooks
from compiler.state import GraphState
import logging
from typing import Any, cast
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


def route_after_review(state: GraphState) -> str:
    if state.get("status") == "approved":
        return "publish"

    if state["revision_count"] >= 3:
        logger.warning(
            f"Draft has been revised {state['revision_count']} times without approval. Escalating to human review."
        )
        return "human_review"

    return "draft"


def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("draft", cast(Any, apply_hooks("draft", draft_node)))
    workflow.add_node("review", cast(Any, apply_hooks("review", review_node)))
    workflow.add_node("publish", cast(Any, apply_hooks("publish", publish_node)))
    workflow.add_node(
        "human_review", cast(Any, apply_hooks("human_review", human_review_node))
    )

    workflow.set_entry_point("draft")
    workflow.add_edge("draft", "review")

    workflow.add_conditional_edges(
        "review",
        route_after_review,
        {
            "publish": "publish",
            "draft": "draft",
            "human_review": "human_review",
        },
    )

    workflow.add_edge("publish", END)
    workflow.add_edge("human_review", END)

    return workflow.compile()
