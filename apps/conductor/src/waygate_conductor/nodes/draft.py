from waygate_core.files.template import render_draft_document
import frontmatter
from waygate_conductor.registry import storage
from waygate_core.logging import get_logger
from waygate_core.schema import GraphState

logger = get_logger()


def draft_node(state: GraphState) -> GraphState:
    """
    Draft node for the compiler graph.
    """
    logger.info("processing draft...", node="draft", revision=state.revision_count)

    source_docs = []

    for doc in state.source_documents:
        try:
            content = storage.read_document(doc)
        except Exception as e:
            logger.error(f"failed to retrieve document {doc}: {e}")
            continue

        # get the document frontmatter and content, and render the draft document text
        metadata, content = frontmatter.parse(content)
        context_data = {
            "source_type": metadata.get("source_type", "unknown"),
            "source_id": metadata.get("source_id", "unknown"),
            "source_uri": metadata.get("source_uri", "unknown"),
            "timestamp": metadata.get("timestamp", "unknown"),
            "topics": metadata.get("topics", []),
            "tags": metadata.get("tags", []),
        }
        rendered_doc = render_draft_document(
            context=context_data, content=content, doc_uri=doc
        )

        source_docs.append(rendered_doc)

    return state
