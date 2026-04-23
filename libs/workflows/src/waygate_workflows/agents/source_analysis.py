from __future__ import annotations

from waygate_core.logging import get_logger

from waygate_workflows.agents.document_analysis import analyze_document_with_supervisor
from waygate_workflows.schema import DocumentAnalysisPromptContext
from waygate_workflows.schema import DocumentAnalysisResultModel
from waygate_workflows.schema import SourceDocumentState

logger = get_logger(__name__)


def analyze_source_document(
    document: SourceDocumentState,
    prompt_context: DocumentAnalysisPromptContext,
    *,
    metadata_model_name: str,
    draft_model_name: str,
) -> DocumentAnalysisResultModel:
    """Run the configured source-analysis implementation for one document.

    Args:
        document: Active source document.
        prompt_context: Reconstructed bounded prompt context for the pass.
        metadata_model_name: Configured metadata model name.
        draft_model_name: Configured draft model name.

    Returns:
        Structured document-analysis result.
    """
    logger.debug(
        "Delegating source document analysis",
        document_uri=document["uri"],
        metadata_model_name=metadata_model_name,
        draft_model_name=draft_model_name,
        prior_brief_count=len(prompt_context["prior_briefs_subset"]),
    )
    result = analyze_document_with_supervisor(
        document,
        prompt_context,
        metadata_model_name=metadata_model_name,
        draft_model_name=draft_model_name,
    )
    logger.debug(
        "Completed source document analysis delegation",
        document_uri=document["uri"],
        topic_count=len(result.metadata.topics),
        key_claim_count=len(result.findings.key_claims),
    )
    return result


__all__ = ["analyze_source_document"]
