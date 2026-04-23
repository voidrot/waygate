from __future__ import annotations

from waygate_core import get_app_context
from waygate_core.logging import get_logger

from waygate_workflows.agents.synthesis import synthesize_draft_with_specialist
from waygate_workflows.runtime.text import preview_text
from waygate_workflows.schema import DraftGraphState, DraftWorkflowStatus

logger = get_logger(__name__)


def synthesize_draft(state: DraftGraphState) -> dict[str, object]:
    """Run the synthesis specialist and advance the workflow into review.

    Args:
        state: Current draft workflow state.

    Returns:
        Partial state update with the synthesized draft and review status.
    """
    logger.info(
        "Starting draft synthesis",
        source_set_key=state.get("source_set_key"),
        summary_count=len(state["document_summaries"]),
        metadata_count=len(state["extracted_metadata"]),
        revision_count=state["revision_count"],
    )
    core_settings = get_app_context().config.core
    draft = synthesize_draft_with_specialist(
        state,
        draft_model_name=core_settings.draft_model_name,
    )
    if not draft:
        logger.warning(
            "Draft synthesis produced empty content",
            source_set_key=state.get("source_set_key"),
            revision_count=state["revision_count"],
        )
    else:
        logger.info(
            "Draft synthesis completed",
            source_set_key=state.get("source_set_key"),
            revision_count=state["revision_count"],
            draft_length=len(draft),
        )
        logger.debug(
            "Draft synthesis preview",
            source_set_key=state.get("source_set_key"),
            draft_preview=preview_text(draft),
        )
    return {
        "current_draft": draft,
        "status": DraftWorkflowStatus.REVIEW,
        "human_review_action": None,
    }
