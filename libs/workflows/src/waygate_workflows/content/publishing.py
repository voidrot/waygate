from __future__ import annotations

from datetime import UTC, datetime

from waygate_core.files import render_compiled_document
from waygate_core.schema import CompiledDocument, DraftDocument, SourceDocumentReference

from waygate_workflows.runtime.text import normalize_string_list
from waygate_workflows.schema import DocumentMetadataState
from waygate_workflows.schema import DraftGraphState


def aggregate_metadata(
    metadata_entries: list[DocumentMetadataState],
) -> dict[str, list[str]]:
    """Aggregate per-document metadata into compiled frontmatter fields."""
    aggregated = {
        "tags": [],
        "topics": [],
        "people": [],
        "organizations": [],
        "projects": [],
    }
    for entry in metadata_entries:
        for key in aggregated:
            aggregated[key].extend(entry.get(key, []))
    return {key: normalize_string_list(values) for key, values in aggregated.items()}


def build_draft_document(state: DraftGraphState) -> DraftDocument:
    """Project workflow state into the validated draft document model."""

    aggregated = aggregate_metadata(state["extracted_metadata"])
    return DraftDocument(
        source_set_key=state["source_set_key"] or "",
        source_documents=[
            SourceDocumentReference(
                uri=doc["uri"],
                content_hash=doc.get("content_hash"),
                source_hash=doc.get("source_hash"),
                source_uri=doc.get("source_uri"),
                source_type=doc.get("source_type"),
                timestamp=doc.get("timestamp"),
            )
            for doc in state["source_documents"]
        ],
        review_feedback=state["review_feedback"],
        content=state["current_draft"],
        **aggregated,
    )


def build_compiled_document(
    state: DraftGraphState,
    *,
    compiled_document_id: str,
    compiled_at: datetime | None = None,
) -> CompiledDocument:
    """Build the durable compiled document model from draft workflow state."""

    draft_document = build_draft_document(state)
    return CompiledDocument(
        doc_id=compiled_document_id,
        source_set_key=draft_document.source_set_key,
        source_documents=draft_document.source_documents,
        compiled_at=compiled_at or datetime.now(tz=UTC),
        review_feedback=draft_document.review_feedback,
        topics=draft_document.topics,
        tags=draft_document.tags,
        people=draft_document.people,
        organizations=draft_document.organizations,
        projects=draft_document.projects,
        content=draft_document.content,
    )


def render_compiled_artifact(
    state: DraftGraphState,
    *,
    compiled_document_id: str,
) -> str:
    """Render the approved compile artifact with frontmatter."""

    compiled_document = build_compiled_document(
        state,
        compiled_document_id=compiled_document_id,
    )
    return render_compiled_document(compiled_document)
