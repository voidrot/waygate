from __future__ import annotations

import json

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from waygate_workflows.runtime.llm import resolve_chat_model
from waygate_workflows.schema import ContinuityExtractionModel
from waygate_workflows.schema import DocumentAnalysisPromptContext
from waygate_workflows.schema import DocumentAnalysisResultModel
from waygate_workflows.schema import FindingsExtractionModel
from waygate_workflows.schema import MetadataExtractionModel
from waygate_workflows.schema import SourceDocumentState
from waygate_workflows.schema import SummaryExtractionModel
from waygate_workflows.tools import build_source_analysis_tools


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
        model=resolve_chat_model(
            "compile",
            metadata_model_name,
            target_name="compile.source-analysis.metadata",
            requires_structured_output=True,
        ),
        tools=[],
        response_format=ToolStrategy(MetadataExtractionModel),
        system_prompt=(
            "You are the metadata extraction specialist for the compile workflow. "
            "Return only grounded tags, topics, people, organizations, and projects for the active document. "
            "Prefer consistency with the provided rolling compile context when the document supports it."
        ),
    )
    summary_agent = create_agent(
        model=resolve_chat_model(
            "compile",
            draft_model_name,
            target_name="compile.source-analysis.summary",
            requires_structured_output=True,
        ),
        tools=[],
        response_format=ToolStrategy(SummaryExtractionModel),
        system_prompt=(
            "You are the document summarization specialist for the compile workflow. "
            "Return a concise narrative summary for the active document. "
            "Use the rolling compile context only to keep terminology and cross-document references consistent."
        ),
    )
    findings_agent = create_agent(
        model=resolve_chat_model(
            "compile",
            draft_model_name,
            target_name="compile.source-analysis.findings",
            requires_structured_output=True,
        ),
        tools=[],
        response_format=ToolStrategy(FindingsExtractionModel),
        system_prompt=(
            "You are the grounded findings specialist for the compile workflow. "
            "Extract only the key grounded claims and defined terms that are materially supported by the active document. "
            "Do not summarize broadly and do not invent claims that are merely implied by prior context."
        ),
    )
    continuity_agent = create_agent(
        model=resolve_chat_model(
            "compile",
            draft_model_name,
            target_name="compile.source-analysis.continuity",
            requires_structured_output=True,
        ),
        tools=[],
        response_format=ToolStrategy(ContinuityExtractionModel),
        system_prompt=(
            "You are the continuity specialist for the compile workflow. "
            "Identify references to prior known entities and any unresolved mentions that should remain open in durable compile state. "
            "Only mark a mention unresolved when the active document clearly points to something that is not fully identified."
        ),
    )

    # The supervisor coordinates the specialist tools but does not bypass them.
    supervisor = create_agent(
        model=resolve_chat_model(
            "compile",
            draft_model_name,
            target_name="compile.source-analysis.supervisor",
            requires_structured_output=True,
        ),
        tools=build_source_analysis_tools(
            document_prompt=document_prompt,
            metadata_agent=metadata_agent,
            summary_agent=summary_agent,
            findings_agent=findings_agent,
            continuity_agent=continuity_agent,
        ),
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
