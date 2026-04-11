from waygate_core.logging import get_logger
from waygate_core.schema import GraphState

logger = get_logger()


def draft_node(state: GraphState) -> GraphState:
    """
    Draft node for the compiler graph.
    """
    logger.info("processing draft...", node="draft", revision=state.revision_count)
    return state
