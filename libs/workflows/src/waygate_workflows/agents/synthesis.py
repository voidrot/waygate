from __future__ import annotations

import json

from langchain.agents import create_agent

from waygate_workflows.runtime.llm import resolve_chat_model
from waygate_workflows.runtime.text import extract_final_text
from waygate_workflows.schema import DraftGraphState


def _build_synthesis_prompt(state: DraftGraphState) -> str:
    """Build the synthesis prompt from durable compile state.

    Args:
        state: Current draft workflow state.

    Returns:
        Prompt payload for the synthesis specialist.
    """
    return (
        f"Source set key: {state['source_set_key']}\n"
        f"Summaries:\n{json.dumps(state['document_summaries'], indent=2, sort_keys=True)}\n\n"
        f"Metadata:\n{json.dumps(state['extracted_metadata'], indent=2, sort_keys=True)}\n\n"
        f"Durable compile context:\n{json.dumps({'canonical_topics': state['canonical_topics'], 'canonical_tags': state['canonical_tags'], 'glossary': state['glossary'], 'entity_registry': state['entity_registry'], 'claim_ledger': state['claim_ledger']}, indent=2, sort_keys=True)}"
    )


def synthesize_draft_with_specialist(
    state: DraftGraphState,
    *,
    draft_model_name: str,
) -> str:
    """Synthesize the final draft from accumulated source-analysis state.

    Args:
        state: Current draft workflow state.
        draft_model_name: Configured draft model name.

    Returns:
        Markdown draft text produced by the synthesis specialist.
    """
    synthesis_agent = create_agent(
        model=resolve_chat_model(
            "compile",
            draft_model_name,
            target_name="compile.synthesis",
        ),
        tools=[],
        system_prompt=(
            "You are the synthesis specialist for the compile workflow. "
            "Combine the analyzed source materials into one cohesive Markdown wiki page. "
            "Eliminate redundancy, preserve grounded claims, and keep terminology consistent with the durable compile context."
        ),
    )
    result = synthesis_agent.invoke(
        {"messages": [{"role": "user", "content": _build_synthesis_prompt(state)}]}
    )
    return extract_final_text(result)


__all__ = ["synthesize_draft_with_specialist"]
