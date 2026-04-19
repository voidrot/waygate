from __future__ import annotations

from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from waygate_workflows.nodes.compile_source_document import compile_source_document
from waygate_workflows.nodes.compile_source_document import (
    route_compile_source_document,
)
from waygate_workflows.nodes.human_review import human_review_gate, route_human_review
from waygate_workflows.nodes.normalize_request import normalize_compile_request
from waygate_workflows.nodes.publish import publish_draft
from waygate_workflows.nodes.review import review_draft, route_review
from waygate_workflows.nodes.synthesis import synthesize_draft
from waygate_workflows.schema import DraftGraphState


def compile_workflow(checkpointer: BaseCheckpointSaver | None = None):
    """Compile the draft workflow graph.

    Args:
        checkpointer: Optional LangGraph checkpointer used for durable state,
            interrupts, and resume support.

    Returns:
        Compiled LangGraph workflow for the draft compile pipeline.
    """
    workflow = StateGraph(cast(Any, DraftGraphState))
    workflow.add_node("normalize_request", normalize_compile_request)
    workflow.add_node("compile_source_document", compile_source_document)
    workflow.add_node("synthesis", synthesize_draft)
    workflow.add_node("review", review_draft)
    workflow.add_node("publish", publish_draft)
    workflow.add_node("human_review", human_review_gate)

    # The graph runs one source-analysis pass per active document until the
    # route function advances to synthesis.
    workflow.add_edge(START, "normalize_request")
    workflow.add_edge("normalize_request", "compile_source_document")
    workflow.add_conditional_edges(
        "compile_source_document",
        route_compile_source_document,
        ["compile_source_document", "synthesis"],
    )
    workflow.add_edge("synthesis", "review")
    workflow.add_conditional_edges(
        "review",
        route_review,
        ["publish", "synthesis", "human_review"],
    )
    workflow.add_conditional_edges(
        "human_review",
        route_human_review,
        ["publish", "synthesis"],
    )
    workflow.add_edge("publish", END)
    return workflow.compile(checkpointer=checkpointer)
