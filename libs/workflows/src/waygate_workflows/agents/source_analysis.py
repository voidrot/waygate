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
    return analyze_document_with_supervisor(
        document,
        prompt_context,
        metadata_model_name=metadata_model_name,
        draft_model_name=draft_model_name,
    )


__all__ = ["analyze_source_document"]
