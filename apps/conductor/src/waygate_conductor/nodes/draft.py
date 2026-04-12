from waygate_core.logging import get_logger
from waygate_core.schema import GraphState

logger = get_logger()


def draft_node(state: GraphState) -> GraphState:
    """
    Draft node for the compiler graph.
    """
    logger.info("processing draft...", node="draft", revision=state.revision_count)

    raw_texts = []

    for doc in state.source_documents:
        try:
            content = storage.read_document(doc)
        except Exception as e:
            logger.error(f"failed to retrieve document {doc}: {e}")
            continue

    return state
