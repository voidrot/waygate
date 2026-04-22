from __future__ import annotations

import json

from waygate_workflows.runtime.llm import invoke_structured_stage
from waygate_workflows.schema import DraftGraphState
from waygate_workflows.schema import ReviewOutcomeModel


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
    return invoke_structured_stage(
        schema=ReviewOutcomeModel,
        workflow_name="compile",
        fallback_model_name=review_model_name,
        target_name="compile.review",
        system_prompt=(
            "You are the review specialist for the compile workflow. "
            "Evaluate the draft for factual grounding, formatting quality, and tone. "
            "Reject the draft when it is not clearly supported by the parsed source set."
        ),
        user_prompt=(
            f"Draft:\n{state['current_draft']}\n\n"
            f"Sources:\n{json.dumps(state['source_documents'], indent=2, sort_keys=True)}"
        ),
    )


__all__ = ["review_draft_with_specialist"]
