from __future__ import annotations

from waygate_core import get_app_context
from waygate_core.logging import get_logger

from waygate_workflows.agents.review import review_draft_with_specialist
from waygate_workflows.runtime.text import normalize_string_list
from waygate_workflows.schema import DraftGraphState, DraftWorkflowStatus

MAX_REVISIONS = 3

logger = get_logger(__name__)


def review_draft(state: DraftGraphState) -> dict[str, object]:
    """Run the review specialist and update approval state.

    Args:
        state: Current draft workflow state.

    Returns:
        Partial state update containing review outcome, feedback, revision count,
        and the resulting workflow status.
    """
    logger.info(
        "Starting draft review",
        source_set_key=state.get("source_set_key"),
        revision_count=state["revision_count"],
        draft_length=len(state["current_draft"]),
        source_document_count=len(state["source_documents"]),
    )
    core_settings = get_app_context().config.core
    result = review_draft_with_specialist(
        state,
        review_model_name=core_settings.review_model_name,
    )
    feedback = normalize_string_list(result.feedback)
    revision_count = state["revision_count"] + (0 if result.approved else 1)
    if result.approved:
        logger.info(
            "Draft review approved publication",
            source_set_key=state.get("source_set_key"),
            revision_count=revision_count,
            feedback_count=len(feedback),
        )
    else:
        logger.warning(
            "Draft review rejected publication",
            source_set_key=state.get("source_set_key"),
            revision_count=revision_count,
            feedback_count=len(feedback),
            max_revisions=MAX_REVISIONS,
        )
    return {
        "review_outcome": {
            "approved": result.approved,
            "feedback": feedback,
        },
        "review_feedback": feedback,
        "revision_count": revision_count,
        "status": (
            DraftWorkflowStatus.APPROVED
            if result.approved
            else DraftWorkflowStatus.REJECTED
        ),
    }


def route_review(state: DraftGraphState) -> str:
    """Choose the next node after review.

    Args:
        state: Current draft workflow state after review.

    Returns:
        ``publish`` for approval, ``human_review`` after exhausting retries, or
        ``synthesis`` to retry draft generation.
    """
    outcome = state.get("review_outcome")
    if outcome and outcome["approved"]:
        logger.info(
            "Routing approved draft to publish",
            source_set_key=state.get("source_set_key"),
            revision_count=state["revision_count"],
        )
        return "publish"
    if state["revision_count"] >= MAX_REVISIONS:
        logger.warning(
            "Routing rejected draft to human review after max revisions",
            source_set_key=state.get("source_set_key"),
            revision_count=state["revision_count"],
            max_revisions=MAX_REVISIONS,
        )
        return "human_review"
    logger.info(
        "Routing rejected draft back to synthesis",
        source_set_key=state.get("source_set_key"),
        revision_count=state["revision_count"],
        feedback_count=len(state["review_feedback"]),
    )
    return "synthesis"
