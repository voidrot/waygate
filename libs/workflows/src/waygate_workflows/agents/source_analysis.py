from __future__ import annotations

from waygate_workflows.agents.document_analysis import analyze_document_with_supervisor
from waygate_workflows.schema import DocumentAnalysisPromptContext
from waygate_workflows.schema import DocumentAnalysisResultModel
from waygate_workflows.schema import SourceDocumentState


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
    return analyze_document_with_supervisor(
        document,
        prompt_context,
        metadata_model_name=metadata_model_name,
        draft_model_name=draft_model_name,
    )


__all__ = ["analyze_source_document"]
