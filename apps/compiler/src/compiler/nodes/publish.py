from datetime import datetime, timezone
from compiler.config import storage
from compiler.state import GraphState
from dataclasses import dataclass

import logging

from waygate_core.doc_helpers import (
    build_compiled_document_id,
    build_live_document_name,
    build_provenance_hash,
    extract_markdown_title,
    generate_frontmatter,
)
from waygate_core.schemas import (
    DocumentType,
    FrontMatterDocument,
    RawDocument,
    SourceMetadataBase,
    SourceType,
    Visibility,
)

logger = logging.getLogger(__name__)


@dataclass
class PromotedMetadata:
    lineage: list[str]
    sources: list[str]
    tags: list[str]
    source_url: str | None
    source_hash: str | None
    source_metadata: dict | None


def _promote_from_raw(
    raw_docs_metadata: list[dict],
) -> PromotedMetadata:
    """Extract lineage, sources, and aggregated tags from raw document metadata.

    Returns:
        (lineage, sources, tags) — each a deduplicated list.
    """
    lineage: list[str] = []
    sources: list[str] = []
    tags: set[str] = set()
    seen_lineage: set[str] = set()
    seen_sources: set[str] = set()
    documents: list[RawDocument] = []
    source_metadata: dict | None = None

    for raw in raw_docs_metadata:
        doc = RawDocument.model_validate(raw)
        documents.append(doc)
        if doc.doc_id not in seen_lineage:
            lineage.append(doc.doc_id)
            seen_lineage.add(doc.doc_id)
        if doc.source_url and doc.source_url not in seen_sources:
            sources.append(doc.source_url)
            seen_sources.add(doc.source_url)
        tags.update(doc.tags)

        if (
            source_metadata is None
            and doc.source_metadata is not None
            and len(raw_docs_metadata) == 1
        ):
            source_metadata = doc.source_metadata.model_dump(exclude_none=True)

    source_url = documents[0].source_url if len(documents) == 1 else None
    return PromotedMetadata(
        lineage=lineage,
        sources=sources,
        tags=sorted(tags),
        source_url=source_url,
        source_hash=build_provenance_hash(documents),
        source_metadata=source_metadata,
    )


def publish_node(state: GraphState) -> dict:
    logger.info("--- PUBLISH: Writing file to live Wiki ---")

    topic = state["target_topic"]
    draft = state.get("current_draft") or ""
    sources_uris = state["new_document_uris"]
    raw_docs_metadata = state.get("raw_documents_metadata", [])
    document_type = state.get("document_type", DocumentType.CONCEPTS.value)

    timestamp = datetime.now(timezone.utc).isoformat()

    promoted = _promote_from_raw(raw_docs_metadata)
    # Fall back to raw storage URIs if no source_url was populated on any document.
    resolved_sources = promoted.sources if promoted.sources else sources_uris
    resolved_title = extract_markdown_title(draft, topic)
    compiled_doc_id = build_compiled_document_id(promoted.lineage, resolved_title)

    frontmatter = generate_frontmatter(
        FrontMatterDocument(
            doc_id=compiled_doc_id,
            title=resolved_title,
            document_type=document_type,
            last_compiled=timestamp,
            last_updated=timestamp,
            source_type=SourceType.SYNTHESIS,
            source_url=promoted.source_url,
            source_hash=promoted.source_hash,
            sources=resolved_sources,
            lineage=promoted.lineage,
            tags=promoted.tags,
            source_metadata=(
                None
                if promoted.source_metadata is None
                else SourceMetadataBase.model_validate(promoted.source_metadata)
            ),
            status="live",
            visibility=Visibility.INTERNAL,
        )
    )

    final_article = f"{frontmatter}\n{draft}"

    file_name = build_live_document_name(resolved_title, compiled_doc_id)

    storage.write_live_document_to_category(
        file_name[:-3], final_article, document_type
    )

    return {"status": "completed"}
