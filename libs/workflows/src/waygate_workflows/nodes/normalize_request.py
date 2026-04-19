from __future__ import annotations

from waygate_workflows.agents.source_normalization import normalize_source_documents
from waygate_workflows.schema import DraftGraphState
from waygate_workflows.schema import DraftWorkflowStatus


def normalize_compile_request(state: DraftGraphState) -> dict[str, object]:
    source_documents, document_order, source_set_key = normalize_source_documents(
        state["raw_documents"]
    )
    active_document = source_documents[0] if source_documents else None
    return {
        "source_documents": source_documents,
        "document_order": document_order,
        "document_cursor": 0,
        "active_document": active_document,
        "source_set_key": source_set_key,
        "status": DraftWorkflowStatus.COMPILING,
        "human_review_action": None,
    }
