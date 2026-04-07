from datetime import datetime, timezone
from compiler.config import storage
from compiler.state import GraphState

import logging

from waygate_core.doc_helpers import generate_frontmatter, slugify
from waygate_core.schemas import (
    FrontMatterDocument,
    RawDocument,
    SourceType,
    Visibility,
)

logger = logging.getLogger(__name__)


def _promote_from_raw(
    raw_docs_metadata: list[dict],
) -> tuple[list[str], list[str], list[str]]:
    """Extract lineage, sources, and aggregated tags from raw document metadata.

    Returns:
        (lineage, sources, tags) — each a deduplicated list.
    """
    lineage: list[str] = []
    sources: list[str] = []
    tags: set[str] = set()

    for raw in raw_docs_metadata:
        doc = RawDocument.model_validate(raw)
        lineage.append(doc.doc_id)
        if doc.source_url:
            sources.append(doc.source_url)
        tags.update(doc.tags)

    return lineage, sources, sorted(tags)


def publish_node(state: GraphState) -> dict:
    logger.info("--- PUBLISH: Writing file to live Wiki ---")

    topic = state["target_topic"]
    draft = state["current_draft"]
    sources_uris = state["new_document_uris"]
    raw_docs_metadata = state.get("raw_documents_metadata", [])

    timestamp = datetime.now(timezone.utc).isoformat()

    lineage, promoted_sources, aggregated_tags = _promote_from_raw(raw_docs_metadata)
    # Fall back to raw storage URIs if no source_url was populated on any document.
    resolved_sources = promoted_sources if promoted_sources else sources_uris

    frontmatter = generate_frontmatter(
        FrontMatterDocument(
            title=topic,
            last_compiled=timestamp,
            last_updated=timestamp,
            source_type=SourceType.SYNTHESIS,
            sources=resolved_sources,
            lineage=lineage,
            tags=aggregated_tags,
            status="live",
            visibility=Visibility.INTERNAL,
        )
    )

    final_article = f"{frontmatter}\n{draft}"

    file_name = f"{slugify(topic)}.md"

    storage.write_live_document(file_name, final_article)

    return {"status": "completed"}
