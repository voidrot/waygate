from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from waygate_workflows.schema import ContinuityExtractionModel
from waygate_workflows.schema import FindingsExtractionModel
from waygate_workflows.schema import MetadataExtractionModel
from waygate_workflows.schema import SummaryExtractionModel


def _invoke_specialist(
    agent: object,
    schema: type[
        MetadataExtractionModel
        | SummaryExtractionModel
        | FindingsExtractionModel
        | ContinuityExtractionModel
    ],
    *,
    document_prompt: str,
) -> str:
    """Invoke a structured specialist agent and serialize its result."""
    result = agent.invoke({"messages": [{"role": "user", "content": document_prompt}]})
    structured = result["structured_response"]
    if not isinstance(structured, schema):
        structured = schema.model_validate(structured)
    return structured.model_dump_json()


def build_source_analysis_tools(
    *,
    document_prompt: str,
    metadata_agent: object,
    summary_agent: object,
    findings_agent: object,
    continuity_agent: object,
) -> list[BaseTool]:
    """Build the callable LangChain tools used by the source-analysis supervisor."""

    @tool
    def extract_document_metadata() -> str:
        """Use the metadata specialist to extract grounded tags, topics, people, organizations, and projects for the active document."""

        return _invoke_specialist(
            metadata_agent,
            MetadataExtractionModel,
            document_prompt=document_prompt,
        )

    @tool
    def summarize_document() -> str:
        """Use the summary specialist to extract a grounded narrative summary for the active document."""

        return _invoke_specialist(
            summary_agent,
            SummaryExtractionModel,
            document_prompt=document_prompt,
        )

    @tool
    def extract_grounded_findings() -> str:
        """Use the findings specialist to extract grounded claims and defined terms for the active document."""

        return _invoke_specialist(
            findings_agent,
            FindingsExtractionModel,
            document_prompt=document_prompt,
        )

    @tool
    def inspect_document_continuity() -> str:
        """Use the continuity specialist to identify prior-context references and unresolved mentions for the active document."""

        return _invoke_specialist(
            continuity_agent,
            ContinuityExtractionModel,
            document_prompt=document_prompt,
        )

    return [
        extract_document_metadata,
        summarize_document,
        extract_grounded_findings,
        inspect_document_continuity,
    ]
