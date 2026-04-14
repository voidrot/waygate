from waygate_core.logging import get_logger
from waygate_core.schema import GraphState

logger = get_logger()


def review_node(state: GraphState) -> GraphState:
    """
    Review node for the compiler graph.
    """
    logger.info("processing review...", node="review", revision=state.revision_count)
    return state
