from waygate_core.logging import get_logger
from waygate_core.schema import GraphState

logger = get_logger()


def metadata_node(state: GraphState) -> GraphState:
    """
    Metadata node for the compiler graph.
    """
    logger.info(
        "processing metadata...", node="metadata", revision=state.revision_count
    )
    return state
