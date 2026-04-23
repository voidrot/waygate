from __future__ import annotations

import json

from waygate_core.logging import get_logger

from waygate_workflows.runtime.llm import invoke_structured_stage
from waygate_workflows.runtime.text import preview_text
from waygate_workflows.schema import DraftGraphState
from waygate_workflows.schema import ReviewOutcomeModel

logger = get_logger(__name__)


def review_draft_with_specialist(
    state: DraftGraphState,
    *,
    review_model_name: str,
) -> ReviewOutcomeModel:
    """Review the synthesized draft against the parsed source documents.

    Args:
        state: Current draft workflow state.
        review_model_name: Configured review model name.

    Returns:
        Structured approval decision and normalized feedback.
    """
    user_prompt = (
        f"Draft:\n{state['current_draft']}\n\n"
        f"Sources:\n{json.dumps(state['source_documents'], indent=2, sort_keys=True)}"
    )
    logger.info(
        "Invoking review specialist",
        source_set_key=state.get("source_set_key"),
        review_model_name=review_model_name,
        source_document_count=len(state["source_documents"]),
        draft_length=len(state["current_draft"]),
    )
    logger.debug(
        "Review specialist draft preview",
        source_set_key=state.get("source_set_key"),
        draft_preview=preview_text(state["current_draft"]),
    )
    result = invoke_structured_stage(
        schema=ReviewOutcomeModel,
        workflow_name="compile",
        fallback_model_name=review_model_name,
        target_name="compile.review",
        system_prompt=(
            "You are the review specialist for the compile workflow. "
            "Evaluate the draft for factual grounding, formatting quality, and tone. "
            "Reject the draft when it is not clearly supported by the parsed source set."
        ),
        user_prompt=user_prompt,
    )
    logger.info(
        "Review specialist completed",
        source_set_key=state.get("source_set_key"),
        approved=result.approved,
        feedback_count=len(result.feedback),
    )
    return result


__all__ = ["review_draft_with_specialist"]
