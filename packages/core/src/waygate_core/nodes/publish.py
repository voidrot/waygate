from waygate_core.logging import get_logger
from waygate_core.nodes.utils import (
    build_publish_document_path,
    build_publish_metadata_path,
    resolve_storage,
    serialize_payload,
)
from waygate_core.schema import DraftGraphState

logger = get_logger()


def publish_node(state: DraftGraphState) -> DraftGraphState:
    """
    Publish node for the compiler graph.
    """
    logger.info("processing publish...", node="publish", revision=state.revision_count)

    storage = resolve_storage()
    processing_errors = list(state.processing_errors)

    if not state.current_documents:
        message = "publish node received no draft documents to persist"
        logger.error(message, node="publish", revision=state.revision_count)
        processing_errors.append(f"publish:{message}")
        return state.model_copy(
            update={
                "status": "publish_failed",
                "review_feedback": message,
                "processing_errors": processing_errors,
            }
        )

    published_uris: list[str] = []
    for document in state.current_documents:
        document_path = build_publish_document_path(
            trace_id=state.runtime_metadata.trace_id,
            file_name=document.file_name,
        )
        published_uris.append(storage.write_document(document_path, document.content))

    metadata_payload = {
        "trace_id": state.runtime_metadata.trace_id,
        "enqueued_at": state.runtime_metadata.enqueued_at,
        "source_documents": state.source_documents,
        "merged_metadata": state.merged_metadata.model_dump(mode="json"),
        "document_metadata": [
            metadata_record.model_dump(mode="json")
            for metadata_record in state.document_metadata
        ],
        "draft_fragments": [
            fragment.model_dump(mode="json") for fragment in state.draft_fragments
        ],
        "published_drafts": published_uris,
    }
    metadata_path = build_publish_metadata_path(state.runtime_metadata.trace_id)
    published_metadata_uri = storage.write_document(
        metadata_path,
        serialize_payload(metadata_payload),
    )

    logger.info(
        "published merged draft and metadata artifacts",
        node="publish",
        draft_count=len(published_uris),
        metadata_uri=published_metadata_uri,
    )
    return state.model_copy(
        update={
            "status": "published",
            "final_drafts": published_uris,
            "published_metadata_uri": published_metadata_uri,
            "processing_errors": processing_errors,
        }
    )
