from __future__ import annotations

import json

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from waygate_core.logging import get_logger

from waygate_workflows.runtime.llm import invoke_structured_stage
from waygate_workflows.runtime.llm import recover_structured_result
from waygate_workflows.runtime.llm import resolve_chat_model
from waygate_workflows.runtime.text import preview_text
from waygate_workflows.schema import ContinuityExtractionModel
from waygate_workflows.schema import DocumentAnalysisPromptContext
from waygate_workflows.schema import DocumentAnalysisResultModel
from waygate_workflows.schema import FindingsExtractionModel
from waygate_workflows.schema import MetadataExtractionModel
from waygate_workflows.schema import SourceDocumentState
from waygate_workflows.schema import SummaryExtractionModel
from waygate_workflows.tools import build_source_analysis_tools

logger = get_logger(__name__)


class _StructuredSpecialistAdapter:
    """Expose a direct structured stage through the agent-like invoke interface."""

    def __init__(
        self,
        *,
        schema: type[
            MetadataExtractionModel
            | SummaryExtractionModel
            | FindingsExtractionModel
            | ContinuityExtractionModel
        ],
        fallback_model_name: str,
        target_name: str,
        system_prompt: str,
    ) -> None:
        self._schema = schema
        self._fallback_model_name = fallback_model_name
        self._target_name = target_name
        self._system_prompt = system_prompt

    def invoke(self, payload: dict[str, object]) -> dict[str, object]:
        """Invoke the structured stage and mirror the create_agent result shape."""

        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("structured specialist requires at least one message")

        first_message = messages[0]
        if not isinstance(first_message, dict):
            raise ValueError("structured specialist messages must be dict objects")

        user_prompt = str(first_message.get("content", ""))
        logger.debug(
            "Invoking structured analysis specialist",
            target_name=self._target_name,
            prompt_length=len(user_prompt),
            prompt_preview=preview_text(user_prompt),
        )
        result = invoke_structured_stage(
            schema=self._schema,
            workflow_name="compile",
            fallback_model_name=self._fallback_model_name,
            target_name=self._target_name,
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
        )
        logger.debug(
            "Structured analysis specialist completed",
            target_name=self._target_name,
            response_type=type(result).__name__,
        )
        return {"structured_response": result}


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


def _extract_structured_response(
    result: dict[str, object],
    schema: type[MetadataExtractionModel]
    | type[SummaryExtractionModel]
    | type[FindingsExtractionModel]
    | type[ContinuityExtractionModel]
    | type[DocumentAnalysisResultModel],
):
    """Return a validated structured response when the agent produced one."""

    return recover_structured_result(schema, result)


def _invoke_specialist_agent(
    agent: object,
    schema: type[MetadataExtractionModel]
    | type[SummaryExtractionModel]
    | type[FindingsExtractionModel]
    | type[ContinuityExtractionModel],
    *,
    document_prompt: str,
):
    """Invoke one specialist directly and require a structured response."""

    logger.debug(
        "Invoking fallback specialist directly",
        target_schema=schema.__name__,
        prompt_length=len(document_prompt),
    )
    result = agent.invoke({"messages": [{"role": "user", "content": document_prompt}]})
    structured = _extract_structured_response(result, schema)
    if structured is None:
        logger.error(
            "Fallback specialist returned no structured response",
            target_schema=schema.__name__,
        )
        raise KeyError("structured_response")
    return structured


def _fallback_document_analysis_result(
    document: SourceDocumentState,
    *,
    document_prompt: str,
    metadata_agent: object,
    summary_agent: object,
    findings_agent: object,
    continuity_agent: object,
) -> DocumentAnalysisResultModel:
    """Build the combined result without relying on supervisor structured output."""

    return DocumentAnalysisResultModel(
        uri=document["uri"],
        metadata=_invoke_specialist_agent(
            metadata_agent,
            MetadataExtractionModel,
            document_prompt=document_prompt,
        ),
        summary=_invoke_specialist_agent(
            summary_agent,
            SummaryExtractionModel,
            document_prompt=document_prompt,
        ),
        findings=_invoke_specialist_agent(
            findings_agent,
            FindingsExtractionModel,
            document_prompt=document_prompt,
        ),
        continuity=_invoke_specialist_agent(
            continuity_agent,
            ContinuityExtractionModel,
            document_prompt=document_prompt,
        ),
    )


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
    logger.info(
        "Starting document analysis supervisor run",
        document_uri=document["uri"],
        metadata_model_name=metadata_model_name,
        draft_model_name=draft_model_name,
        guidance_count=len(prompt_context["prompt_instructions"]),
    )
    document_prompt = _build_document_prompt(document, prompt_context)
    logger.debug(
        "Built document analysis supervisor prompt",
        document_uri=document["uri"],
        prompt_length=len(document_prompt),
        prompt_preview=preview_text(document_prompt),
    )

    metadata_system_prompt = (
        "You are the metadata extraction specialist for the compile workflow. "
        "Return only grounded tags, topics, people, organizations, and projects for the active document. "
        "Prefer consistency with the provided rolling compile context when the document supports it."
    )
    summary_system_prompt = (
        "You are the document summarization specialist for the compile workflow. "
        "Return a concise narrative summary for the active document. "
        "Use the rolling compile context only to keep terminology and cross-document references consistent."
    )
    findings_system_prompt = (
        "You are the grounded findings specialist for the compile workflow. "
        "Extract only the key grounded claims and defined terms that are materially supported by the active document. "
        "Do not summarize broadly and do not invent claims that are merely implied by prior context."
    )
    continuity_system_prompt = (
        "You are the continuity specialist for the compile workflow. "
        "Identify references to prior known entities and any unresolved mentions that should remain open in durable compile state. "
        "Only mark a mention unresolved when the active document clearly points to something that is not fully identified."
    )

    metadata_agent = _StructuredSpecialistAdapter(
        schema=MetadataExtractionModel,
        fallback_model_name=metadata_model_name,
        target_name="compile.source-analysis.metadata",
        system_prompt=metadata_system_prompt,
    )
    summary_agent = _StructuredSpecialistAdapter(
        schema=SummaryExtractionModel,
        fallback_model_name=draft_model_name,
        target_name="compile.source-analysis.summary",
        system_prompt=summary_system_prompt,
    )
    findings_agent = _StructuredSpecialistAdapter(
        schema=FindingsExtractionModel,
        fallback_model_name=draft_model_name,
        target_name="compile.source-analysis.findings",
        system_prompt=findings_system_prompt,
    )
    continuity_agent = _StructuredSpecialistAdapter(
        schema=ContinuityExtractionModel,
        fallback_model_name=draft_model_name,
        target_name="compile.source-analysis.continuity",
        system_prompt=continuity_system_prompt,
    )

    # The supervisor coordinates the specialist tools but does not bypass them.
    supervisor_tools = build_source_analysis_tools(
        document_prompt=document_prompt,
        metadata_agent=metadata_agent,
        summary_agent=summary_agent,
        findings_agent=findings_agent,
        continuity_agent=continuity_agent,
    )
    supervisor = create_agent(
        model=resolve_chat_model(
            "compile",
            draft_model_name,
            target_name="compile.source-analysis.supervisor",
            requires_structured_output=True,
        ),
        tools=supervisor_tools,
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
    structured = _extract_structured_response(
        supervisor_result,
        DocumentAnalysisResultModel,
    )
    if structured is None:
        logger.warning(
            "Document analysis supervisor returned no structured response; falling back to direct specialists",
            document_uri=document["uri"],
        )
        structured = _fallback_document_analysis_result(
            document,
            document_prompt=document_prompt,
            metadata_agent=metadata_agent,
            summary_agent=summary_agent,
            findings_agent=findings_agent,
            continuity_agent=continuity_agent,
        )
    if structured.uri != document["uri"]:
        logger.warning(
            "Document analysis supervisor returned mismatched URI; normalizing to active document",
            expected_uri=document["uri"],
            actual_uri=structured.uri,
        )
        structured.uri = document["uri"]
    logger.info(
        "Completed document analysis supervisor run",
        document_uri=document["uri"],
        topic_count=len(structured.metadata.topics),
        key_claim_count=len(structured.findings.key_claims),
        unresolved_mention_count=len(structured.continuity.unresolved_mentions),
    )
    return structured
