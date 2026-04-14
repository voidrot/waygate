from waygate_core.logging import get_logger
from waygate_core.schema import DraftGraphState

logger = get_logger()


def review_node(state: DraftGraphState) -> DraftGraphState:
    """
    Review node for the compiler graph.
    """
    logger.info("processing review...", node="review", revision=state.revision_count)
    if state.current_draft and state.current_draft.strip():
        return state.model_copy(update={"status": "approved", "review_feedback": None})

    return state.model_copy(
        update={
            "status": "rejected",
            "revision_count": state.revision_count + 1,
            "review_feedback": "No merged draft was produced for review.",
        }
    )
