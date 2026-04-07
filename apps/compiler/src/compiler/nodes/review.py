from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from compiler.state import GraphState
from waygate_core.settings import get_runtime_settings

import logging
from compiler.config import storage
from waygate_core.llm import get_structured_llm

logger = logging.getLogger(__name__)

settings = get_runtime_settings()
review_provider = settings.review_llm_provider
review_model = settings.review_llm_model


class ReviewOutcome(BaseModel):
    approved: bool = Field(
        description="Must be strictly True if the draft is perfect, False if ANY rules are violated."
    )
    feedback: str = Field(
        description="If rejected, a bulleted list of exactly what the Compiler must fix. If approved, leave blank."
    )
    violations: List[str] = Field(
        description="A list of specific rule categories violated (e.g., ['hallucination', 'formatting']). Empty if approved."
    )


def review_node(state: GraphState) -> dict:
    logger.info(
        f"--- REVIEW: Reviewing Draft Revision: {state.get('revision_count', 0)} ---"
    )

    raw_texts = []
    for uri in state["new_document_uris"]:
        try:
            content = storage.read_raw_document(uri)
            raw_texts.append(f"document uri='{uri}'>\n{content}\n</document>")
        except Exception as e:
            logger.error(f"Failed to read document {uri}: {e}")

    compiled_raw_data = "\n\n".join(raw_texts)

    llm = get_structured_llm(review_provider, ReviewOutcome, review_model)

    system_prompt = """
    You are Hermes, an automated Quality Assurance Editor for a technical knowledge base.
    Your job is to ruthlessly evaluate the provided Markdown draft against the raw source documents.

    EVALUATION RULES:
    1. Grounding: The draft MUST NOT contain any facts, metrics, or claims that are not explicitly supported by the <raw_data>.
    2. Formatting: The draft MUST be valid Markdown. It must use proper headers (##, ###), lists, and code blocks.
    3. Tone: The draft MUST read like a sterile wiki article. Reject any draft that contains conversational filler (e.g., "Here is the summary," "In conclusion," "Certainly!").
    4. Completeness: The draft must synthesize the raw data meaningfully, not just copy-paste it.

    If ALL rules are met, output approved: true.
    If ANY rule is broken, output approved: false, and provide specific, actionable feedback for the writer to fix.
    """

    user_prompt = f"""
    TARGET TOPIC: {state["target_topic"]}

    SOURCE MATERIAL:
    <raw_data>
    {compiled_raw_data}
    </raw_data>

    DRAFT TO EVALUATE:
    <draft>
    {state["current_draft"]}
    </draft>
    """

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

    response = llm.invoke(messages)

    logger.info(
        f"Review Outcome: approved={response.approved}, feedback={response.feedback}, violations={response.violations}"
    )

    return {
        "status": "approved" if response.approved else "rejected",
        "qa_feedback": response.feedback,
    }
