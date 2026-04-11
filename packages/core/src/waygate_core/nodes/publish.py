from waygate_core.logging import get_logger
from waygate_core.schema import GraphState

logger = get_logger()


def publish_node(state: GraphState) -> GraphState:
    """
    Publish node for the compiler graph.
    """
    logger.info("processing publish...", node="publish", revision=state.revision_count)
    return state
