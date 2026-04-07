import logging

from compiler.graph import build_graph
from compiler.state import GraphState


logger = logging.getLogger(__name__)


def execute_graph(initial_state: dict):
    trace_id = initial_state.get("trace_id", "unknown")
    logger.info(
        "Executing graph trace_id=%s with initial state: %s", trace_id, initial_state
    )

    execution_state: GraphState = GraphState(**initial_state)

    workflow_app = build_graph()

    final_state = workflow_app.invoke(execution_state)

    logger.info(
        "Graph execution completed trace_id=%s with final state: %s",
        trace_id,
        final_state,
    )

    return final_state
