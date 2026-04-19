from __future__ import annotations

import json

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import tool

from waygate_workflows.agents.common import resolve_chat_model
from waygate_workflows.schema import ContinuityExtractionModel
from waygate_workflows.schema import DocumentAnalysisPromptContext
from waygate_workflows.schema import DocumentAnalysisResultModel
from waygate_workflows.schema import FindingsExtractionModel
from waygate_workflows.schema import MetadataExtractionModel
from waygate_workflows.schema import SourceDocumentState
from waygate_workflows.schema import SummaryExtractionModel


def _build_document_prompt(
    document: SourceDocumentState,
    prompt_context: DocumentAnalysisPromptContext,
) -> str:
    """Build the shared user prompt for document-analysis specialists.

    Args:
        document: Active source document.
        prompt_context: Reconstructed bounded prompt context for the pass.

    Returns:
        Prompt payload combining the rolling context and document body.
    """
    return (
        f"Prompt context:\n{json.dumps(prompt_context, indent=2, sort_keys=True)}\n\n"
        f"Document URI: {document['uri']}\n"
        f"Document content:\n{document['content']}"
    )


def _coerce_model(
    schema: type[MetadataExtractionModel]
    | type[SummaryExtractionModel]
    | type[FindingsExtractionModel]
    | type[ContinuityExtractionModel]
    | type[DocumentAnalysisResultModel],
    value: object,
):
    """Coerce provider output into the expected structured response model.

    Args:
        schema: Expected Pydantic model type.
        value: Raw provider output.

    Returns:
        Parsed model instance.
    """
    if isinstance(value, schema):
        return value
    return schema.model_validate(value)


def analyze_document_with_supervisor(
    document: SourceDocumentState,
    prompt_context: DocumentAnalysisPromptContext,
    *,
    metadata_model_name: str,
    draft_model_name: str,
) -> DocumentAnalysisResultModel:
    """Analyze one source document with a supervisor and specialist subagents.

    Args:
        document: Active source document.
        prompt_context: Reconstructed bounded prompt context for the pass.
        metadata_model_name: Configured metadata model name.
        draft_model_name: Configured general draft model name.

    Returns:
        Combined structured analysis result for the active document.
    """
    document_prompt = _build_document_prompt(document, prompt_context)

    metadata_agent = create_agent(
        model=resolve_chat_model("metadata", metadata_model_name),
        tools=[],
        response_format=ToolStrategy(MetadataExtractionModel),
        system_prompt=(
            "You are the metadata extraction specialist for the compile workflow. "
            "Return only grounded tags, topics, people, organizations, and projects for the active document. "
            "Prefer consistency with the provided rolling compile context when the document supports it."
        ),
    )
    summary_agent = create_agent(
        model=resolve_chat_model("draft", draft_model_name),
        tools=[],
        response_format=ToolStrategy(SummaryExtractionModel),
        system_prompt=(
            "You are the document summarization specialist for the compile workflow. "
            "Return a concise narrative summary for the active document. "
            "Use the rolling compile context only to keep terminology and cross-document references consistent."
        ),
    )
    findings_agent = create_agent(
        model=resolve_chat_model("draft", draft_model_name),
        tools=[],
        response_format=ToolStrategy(FindingsExtractionModel),
        system_prompt=(
            "You are the grounded findings specialist for the compile workflow. "
            "Extract only the key grounded claims and defined terms that are materially supported by the active document. "
            "Do not summarize broadly and do not invent claims that are merely implied by prior context."
        ),
    )
    continuity_agent = create_agent(
        model=resolve_chat_model("draft", draft_model_name),
        tools=[],
        response_format=ToolStrategy(ContinuityExtractionModel),
        system_prompt=(
            "You are the continuity specialist for the compile workflow. "
            "Identify references to prior known entities and any unresolved mentions that should remain open in durable compile state. "
            "Only mark a mention unresolved when the active document clearly points to something that is not fully identified."
        ),
    )

    @tool
    def extract_document_metadata() -> str:
        """Use the metadata specialist to extract grounded tags, topics, people, organizations, and projects for the active document."""

        result = metadata_agent.invoke(
            {"messages": [{"role": "user", "content": document_prompt}]}
        )
        structured = _coerce_model(
            MetadataExtractionModel,
            result["structured_response"],
        )
        return structured.model_dump_json()

    @tool
    def summarize_document() -> str:
        """Use the summary specialist to extract a grounded narrative summary for the active document."""

        result = summary_agent.invoke(
            {"messages": [{"role": "user", "content": document_prompt}]}
        )
        structured = _coerce_model(
            SummaryExtractionModel,
            result["structured_response"],
        )
        return structured.model_dump_json()

    @tool
    def extract_grounded_findings() -> str:
        """Use the findings specialist to extract grounded claims and defined terms for the active document."""

        result = findings_agent.invoke(
            {"messages": [{"role": "user", "content": document_prompt}]}
        )
        structured = _coerce_model(
            FindingsExtractionModel,
            result["structured_response"],
        )
        return structured.model_dump_json()

    @tool
    def inspect_document_continuity() -> str:
        """Use the continuity specialist to identify prior-context references and unresolved mentions for the active document."""

        result = continuity_agent.invoke(
            {"messages": [{"role": "user", "content": document_prompt}]}
        )
        structured = _coerce_model(
            ContinuityExtractionModel,
            result["structured_response"],
        )
        return structured.model_dump_json()

    # The supervisor coordinates the specialist tools but does not bypass them.
    supervisor = create_agent(
        model=resolve_chat_model("draft", draft_model_name),
        tools=[
            extract_document_metadata,
            summarize_document,
            extract_grounded_findings,
            inspect_document_continuity,
        ],
        response_format=ToolStrategy(DocumentAnalysisResultModel),
        system_prompt=(
            "You are the document-analysis supervisor for the compile workflow. "
            "For each document, delegate to the available specialists instead of doing the analysis yourself. "
            "Call each specialist exactly once, then return the combined structured result. "
            "Do not invent content that is not supported by the active document and rolling compile context."
        ),
    )
    supervisor_result = supervisor.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Analyze the active document and combine the specialist outputs into one structured result.\n\n{document_prompt}"
                    ),
                }
            ]
        }
    )
    structured = _coerce_model(
        DocumentAnalysisResultModel,
        supervisor_result["structured_response"],
    )
    if structured.uri != document["uri"]:
        structured.uri = document["uri"]
    return structured
