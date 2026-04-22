from __future__ import annotations

import json

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from waygate_workflows.runtime.llm import resolve_chat_model
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
    review_agent = create_agent(
        model=resolve_chat_model(
            "compile",
            review_model_name,
            target_name="compile.review",
            requires_structured_output=True,
        ),
        tools=[],
        response_format=ToolStrategy(ReviewOutcomeModel),
        system_prompt=(
            "You are the review specialist for the compile workflow. "
            "Evaluate the draft for factual grounding, formatting quality, and tone. "
            "Reject the draft when it is not clearly supported by the parsed source set."
        ),
    )
    result = review_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Draft:\n{state['current_draft']}\n\n"
                        f"Sources:\n{json.dumps(state['source_documents'], indent=2, sort_keys=True)}"
                    ),
                }
            ]
        }
    )
    structured = result["structured_response"]
    if isinstance(structured, ReviewOutcomeModel):
        return structured
    return ReviewOutcomeModel.model_validate(structured)


__all__ = ["review_draft_with_specialist"]
