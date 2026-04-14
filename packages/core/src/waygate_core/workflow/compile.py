from waygate_core.nodes.publish import publish_node
from waygate_core.nodes.human import human_review_node
from waygate_core.nodes.review import review_node
from waygate_core.nodes.metadata import metadata_node
from waygate_core.nodes.draft import draft_node
from waygate_core.logging import get_logger
from waygate_core.schema import DraftGraphState
from langgraph.graph import StateGraph, END

logger = get_logger()


def route_after_review(state: DraftGraphState) -> str:
    if state.status == "approved":
        logger.debug(
            "review approved, routing to publish",
            node="review",
            action="routing",
            target="publish",
            revision=state.revision_count,
        )
        return "publish"

    if state.revision_count >= 3:
        logger.warning(
            "review rejected after 3 revisions, routing to human review",
            node="review",
            action="routing",
            target="human_review",
            revision=state.revision_count,
        )
        return "human_review"

    logger.info(
        "review rejected, routing back to draft",
        node="review",
        action="routing",
        target="draft",
        revision=state.revision_count,
    )
    return "draft"


def compile_graph() -> StateGraph[DraftGraphState]:

    workflow = StateGraph(DraftGraphState)

    # set the entry point of the graph
    workflow.set_entry_point("metadata")

    # Add nodes to the graph
    workflow.add_node("draft", draft_node)
    workflow.add_node("metadata", metadata_node)
    workflow.add_node("review", review_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("publish", publish_node)

    # Add edges to define the flow of the graph
    workflow.add_edge("metadata", "draft")
    workflow.add_edge("draft", "review")
    workflow.add_edge("publish", END)
    workflow.add_edge("human_review", END)

    # Add a conditional edge based on the review outcome
    workflow.add_conditional_edges(
        "review",
        route_after_review,
        {
            "publish": "publish",
            "draft": "draft",
            "human_review": "human_review",
        },
    )

    return workflow
