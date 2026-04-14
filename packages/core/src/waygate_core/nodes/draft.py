from waygate_core.logging import get_logger
from waygate_core.nodes.utils import (
    generate_draft_fragment,
    merge_draft_fragments,
    read_source_document,
    resolve_storage,
)
from waygate_core.schema import DraftGraphState
from waygate_core.schema.document import (
    DocumentMetadataRecord,
    DraftDocument,
    DraftFragment,
)

logger = get_logger()


def draft_node(state: DraftGraphState) -> DraftGraphState:
    """
    Draft node for the compiler graph.
    """
    logger.info("processing draft...", node="draft", revision=state.revision_count)

    storage = resolve_storage()
    processing_errors = list(state.processing_errors)
    draft_fragments: list[DraftFragment] = []
    metadata_by_source = {
        metadata_record.source_document: metadata_record
        for metadata_record in state.document_metadata
    }
    fragment_summaries: list[str] = []

    for doc in state.source_documents:
        try:
            frontmatter_model, content = read_source_document(doc, storage)
        except Exception as exc:
            logger.error(
                "failed to retrieve source document",
                node="draft",
                source_document=doc,
                error=str(exc),
            )
            processing_errors.append(f"draft-read:{doc}:{exc}")
            continue

        document_metadata = metadata_by_source.get(
            doc,
            DocumentMetadataRecord(
                source_document=doc,
                source_type=frontmatter_model.source_type,
                source_id=frontmatter_model.source_id,
                source_uri=frontmatter_model.source_uri,
                source_hash=frontmatter_model.source_hash,
                topics=frontmatter_model.topics,
                tags=frontmatter_model.tags,
            ),
        )

        try:
            fragment = generate_draft_fragment(
                doc_uri=doc,
                content=content,
                document_metadata=document_metadata,
                merged_metadata=state.merged_metadata,
                prior_summaries=fragment_summaries,
            )
        except Exception as exc:
            logger.error(
                "failed to generate draft fragment",
                node="draft",
                source_document=doc,
                error=str(exc),
            )
            processing_errors.append(f"draft-fragment:{doc}:{exc}")
            continue

        draft_fragments.append(fragment)
        if fragment.summary:
            fragment_summaries.append(fragment.summary)

    merged_draft = merge_draft_fragments(draft_fragments, state.merged_metadata)
    current_documents = []
    if merged_draft:
        current_documents.append(
            DraftDocument(
                content=merged_draft,
                file_name="merged-draft.md",
                topics=state.merged_metadata.topics,
                tags=state.merged_metadata.tags,
                people=state.merged_metadata.people,
                organizations=state.merged_metadata.organizations,
                projects=state.merged_metadata.projects,
                sources=list(state.source_documents),
                project=(
                    state.merged_metadata.projects[0]
                    if state.merged_metadata.projects
                    else None
                ),
                organization=(
                    state.merged_metadata.organizations[0]
                    if state.merged_metadata.organizations
                    else None
                ),
            )
        )

    return state.model_copy(
        update={
            "status": "draft",
            "draft_fragments": draft_fragments,
            "current_draft": merged_draft or None,
            "current_documents": current_documents,
            "processing_errors": processing_errors,
        }
    )
