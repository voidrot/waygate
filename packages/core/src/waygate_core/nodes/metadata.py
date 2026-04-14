from waygate_core.logging import get_logger
from waygate_core.schema import DraftGraphState
from waygate_core.nodes.utils import (
    extract_document_metadata,
    merge_metadata_records,
    read_source_document,
    resolve_storage,
)

logger = get_logger()


def metadata_node(state: DraftGraphState) -> DraftGraphState:
    """
    Metadata node for the compiler graph.
    """
    logger.info(
        "processing metadata...", node="metadata", revision=state.revision_count
    )

    storage = resolve_storage()
    document_metadata = list(state.document_metadata)
    processing_errors = list(state.processing_errors)
    running_memory = state.merged_metadata

    for doc in state.source_documents:
        logger.debug("processing source document", source_document=doc, node="metadata")
        try:
            frontmatter_model, content = read_source_document(doc, storage)
            metadata_record = extract_document_metadata(
                doc_uri=doc,
                content=content,
                frontmatter_model=frontmatter_model,
                running_memory=running_memory,
            )
            document_metadata.append(metadata_record)
            running_memory = merge_metadata_records(
                [metadata_record], base=running_memory
            )
        except Exception as exc:
            logger.error(
                "failed to process source document metadata",
                node="metadata",
                source_document=doc,
                error=str(exc),
            )
            processing_errors.append(f"metadata:{doc}:{exc}")

    merged_metadata = merge_metadata_records(document_metadata)
    return state.model_copy(
        update={
            "status": "metadata",
            "merged_metadata": merged_metadata,
            "document_metadata": document_metadata,
            "topics": merged_metadata.topics,
            "tags": merged_metadata.tags,
            "people": merged_metadata.people,
            "organizations": merged_metadata.organizations,
            "projects": merged_metadata.projects,
            "established_terms": merged_metadata.established_terms,
            "covered_topics": merged_metadata.topics,
            "discovered_tags": merged_metadata.tags,
            "processing_errors": processing_errors,
        }
    )
