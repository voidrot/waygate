import logging

from compiler.graph import build_graph
from compiler.state import GraphState


logger = logging.getLogger(__name__)


def execute_graph(initial_state: dict):

    logger.info(f"Executing graph with initial state: {initial_state}")

    execution_state: GraphState = GraphState(**initial_state)

    workflow_app = build_graph()

    final_state = workflow_app.invoke(execution_state)

    logger.info(f"Graph execution completed with final state: {final_state}")

    return final_state
