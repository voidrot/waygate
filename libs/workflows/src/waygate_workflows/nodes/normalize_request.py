from __future__ import annotations

from waygate_core.logging import get_logger

from waygate_workflows.agents.source_normalization import normalize_source_documents
from waygate_workflows.schema import DraftGraphState
from waygate_workflows.schema import DraftWorkflowStatus

logger = get_logger(__name__)


def normalize_compile_request(state: DraftGraphState) -> dict[str, object]:
    """Normalize raw trigger input into the initial compile loop state.

    Args:
        state: Draft workflow state at graph entry.

    Returns:
        Partial state update containing parsed documents, ordering metadata, and
        the first active document.
    """
    logger.info(
        "Normalizing compile request",
        source=state["source"],
        raw_document_count=len(state["raw_documents"]),
    )
    source_documents, document_order, source_set_key = normalize_source_documents(
        state["raw_documents"]
    )
    active_document = source_documents[0] if source_documents else None
    if not source_documents:
        logger.warning(
            "Compile request normalization produced no source documents",
            source=state["source"],
        )
    else:
        logger.info(
            "Compile request normalization completed",
            source=state["source"],
            source_set_key=source_set_key,
            document_count=len(source_documents),
            first_document_uri=active_document["uri"] if active_document else None,
        )
    return {
        "source_documents": source_documents,
        "document_order": document_order,
        "document_cursor": 0,
        "active_document": active_document,
        "source_set_key": source_set_key,
        "status": DraftWorkflowStatus.COMPILING,
        "human_review_action": None,
    }
