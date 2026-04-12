from waygate_core.logging import get_logger
from waygate_core.schema import GraphState

logger = get_logger()


def human_review_node(state: GraphState) -> GraphState:
    """
    Human review node for the compiler graph.
    """
    logger.info(
        "processing human review...", node="human_review", revision=state.revision_count
    )
    return state
