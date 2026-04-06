import logging
from compiler.config import storage
from langchain_core.messages import HumanMessage, SystemMessage
from waygate_core.llm import get_llm
from compiler.state import GraphState
import os

logger = logging.getLogger(__name__)

draft_model = os.getenv("DRAFT_LLM_MODEL", "gemma4:e4b")
draft_provider = os.getenv("DRAFT_LLM_PROVIDER", "ollama")


def draft_node(state: GraphState):
    logger.info(
        f"--- DRAFT: Current Revision: {state.get('revision_count', 0) + 1} ---"
    )

    raw_texts = []
    for uri in state["new_document_uris"]:
        try:
            content = storage.read_raw_document(uri)
            raw_texts.append(f"document uri='{uri}'>\n{content}\n</document>")
        except Exception as e:
            logger.error(f"Failed to read document {uri}: {e}")

    compiled_raw_data = "\n\n".join(raw_texts)

    llm = get_llm(draft_provider, draft_model)

    feedback_section = ""
    if state.get("qa_feedback"):
        feedback_section = f"""
        WARNING: Your previous draft was rejected by the Quality Assurance system.
        You MUST fix the following issues in your new draft:
        <feedback>
        {state["qa_feedback"]}
        </feedback>
        """

    system_prompt = f"""
    You are an expert technical writer and knowledge base compiler.
    Your task is to synthesize the provided raw documents into a highly organized,
    comprehensive Markdown article about '{state["target_topic"]}'.

    Guidelines:
    - Use clear headers, bullet points, and code blocks where applicable.
    - Do not invent information; rely ONLY on the provided raw documents.
    - Include internal markdown backlinks if you reference other concepts.

    {feedback_section}
    """

    user_prompt = f"""
    Here are the raw documents to synthesize:

    <raw_data>
    {compiled_raw_data}
    </raw_data>

    Please generate the complete markdown article.
    """

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

    response = llm.invoke(messages)

    return {
        "current_draft": response.content,
        "revision_count": state.get("revision_count", 0) + 1,
        "status": "reviewing",
    }
