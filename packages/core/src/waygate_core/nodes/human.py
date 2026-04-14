from waygate_core.logging import get_logger
from waygate_core.schema import DraftGraphState

logger = get_logger()


def human_review_node(state: DraftGraphState) -> DraftGraphState:
    """
    Human review node for the compiler graph.
    """
    logger.info(
        "processing human review...", node="human_review", revision=state.revision_count
    )
    return state
