from __future__ import annotations

from waygate_core import get_app_context

from waygate_workflows.agents.synthesis import synthesize_draft_with_specialist
from waygate_workflows.schema import DraftGraphState, DraftWorkflowStatus


def synthesize_draft(state: DraftGraphState) -> dict[str, object]:
    """Run the synthesis specialist and advance the workflow into review.

    Args:
        state: Current draft workflow state.

    Returns:
        Partial state update with the synthesized draft and review status.
    """
    core_settings = get_app_context().config.core
    draft = synthesize_draft_with_specialist(
        state,
        draft_model_name=core_settings.draft_model_name,
    )
    return {
        "current_draft": draft,
        "status": DraftWorkflowStatus.REVIEW,
        "human_review_action": None,
    }
