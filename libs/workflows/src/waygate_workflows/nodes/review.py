from __future__ import annotations

from waygate_core import get_app_context

from waygate_workflows.agents.review import review_draft_with_specialist
from waygate_workflows.runtime.text import normalize_string_list
from waygate_workflows.schema import DraftGraphState, DraftWorkflowStatus

MAX_REVISIONS = 3


def review_draft(state: DraftGraphState) -> dict[str, object]:
    """Run the review specialist and update approval state.

    Args:
        state: Current draft workflow state.

    Returns:
        Partial state update containing review outcome, feedback, revision count,
        and the resulting workflow status.
    """
    core_settings = get_app_context().config.core
    result = review_draft_with_specialist(
        state,
        review_model_name=core_settings.review_model_name,
    )
    feedback = normalize_string_list(result.feedback)
    revision_count = state["revision_count"] + (0 if result.approved else 1)
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
        return "publish"
    if state["revision_count"] >= MAX_REVISIONS:
        return "human_review"
    return "synthesis"
