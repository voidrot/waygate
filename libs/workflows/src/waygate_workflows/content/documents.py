from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import frontmatter
from waygate_core.files import compute_content_hash, normalize_document_body

from waygate_workflows.schema import OrderedDocumentRef
from waygate_workflows.schema import SourceDocumentState


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
    post = frontmatter.loads(raw_content)
    metadata = post.metadata
    normalized_content = normalize_document_body(post.content)
    return {
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
        raise ValueError("Compile workflow requires at least one source document")

    content_hashes = [document.get("content_hash") for document in documents]
    if all(content_hashes):
        payload = "\n".join(sorted(str(value) for value in content_hashes))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"hash-{digest}"

    raise ValueError(
        "Compile workflow requires content_hash coverage for the source set"
    )
