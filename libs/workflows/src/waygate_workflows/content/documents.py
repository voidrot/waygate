from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import frontmatter
from waygate_core.files import compute_content_hash, normalize_document_body
from waygate_core.logging import get_logger

from waygate_workflows.schema import OrderedDocumentRef
from waygate_workflows.schema import SourceDocumentState

logger = get_logger(__name__)


def normalize_frontmatter_value(value: object) -> str | None:
    """Normalize frontmatter values for storage in workflow state."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    text = str(value).strip()
    return text or None


def parse_source_document(document_uri: str, raw_content: str) -> SourceDocumentState:
    """Parse stored markdown into the normalized source-document state shape."""
    logger.debug(
        "Parsing source document",
        document_uri=document_uri,
        raw_content_length=len(raw_content),
    )
    post = frontmatter.loads(raw_content)
    metadata = post.metadata
    normalized_content = normalize_document_body(post.content)
    parsed = {
        "uri": document_uri,
        "content": normalized_content,
        "content_type": normalize_frontmatter_value(metadata.get("content_type")),
        "content_hash": normalize_frontmatter_value(metadata.get("content_hash"))
        or compute_content_hash(normalized_content),
        "source_hash": normalize_frontmatter_value(metadata.get("source_hash")),
        "source_uri": normalize_frontmatter_value(metadata.get("source_uri")),
        "source_type": normalize_frontmatter_value(metadata.get("source_type")),
        "timestamp": normalize_frontmatter_value(metadata.get("timestamp")),
    }
    logger.debug(
        "Parsed source document",
        document_uri=document_uri,
        content_length=len(normalized_content),
        source_uri=parsed.get("source_uri"),
        source_type=parsed.get("source_type"),
    )
    return parsed


def to_ordered_document_ref(document: SourceDocumentState) -> OrderedDocumentRef:
    """Project a full source document into the lighter ordering reference."""
    return {
        "uri": document["uri"],
        "content_type": document.get("content_type"),
        "content_hash": document.get("content_hash"),
        "source_hash": document.get("source_hash"),
        "source_uri": document.get("source_uri"),
        "source_type": document.get("source_type"),
        "timestamp": document.get("timestamp"),
    }


def derive_source_set_key(documents: list[SourceDocumentState]) -> str:
    """Derive the stable source-set identity for a compile run."""
    if not documents:
        logger.error("Cannot derive source_set_key without source documents")
        raise ValueError("Compile workflow requires at least one source document")

    content_hashes = [document.get("content_hash") for document in documents]
    if all(content_hashes):
        payload = "\n".join(sorted(str(value) for value in content_hashes))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        source_set_key = f"hash-{digest}"
        logger.debug(
            "Derived source_set_key from content hashes",
            document_count=len(documents),
            source_set_key=source_set_key,
        )
        return source_set_key

    logger.error(
        "Cannot derive source_set_key because content_hash coverage is incomplete",
        document_count=len(documents),
    )
    raise ValueError(
        "Compile workflow requires content_hash coverage for the source set"
    )
