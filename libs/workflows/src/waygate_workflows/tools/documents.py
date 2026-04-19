from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import frontmatter

from waygate_workflows.schema import OrderedDocumentRef
from waygate_workflows.schema import SourceDocumentState


def normalize_frontmatter_value(value: object) -> str | None:
    """Normalize frontmatter values for storage in workflow state.

    Args:
        value: Raw frontmatter value from a parsed markdown document.

    Returns:
        String form of the value, or ``None`` when the value is empty.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    text = str(value).strip()
    return text or None


def parse_source_document(document_uri: str, raw_content: str) -> SourceDocumentState:
    """Parse stored markdown into the normalized source-document state shape.

    Args:
        document_uri: Storage URI for the raw document.
        raw_content: Markdown document contents including optional frontmatter.

    Returns:
        Parsed document state used by the compile workflow.
    """
    post = frontmatter.loads(raw_content)
    metadata = post.metadata
    return {
        "uri": document_uri,
        "content": post.content.strip(),
        "source_hash": normalize_frontmatter_value(metadata.get("source_hash")),
        "source_uri": normalize_frontmatter_value(metadata.get("source_uri")),
        "source_type": normalize_frontmatter_value(metadata.get("source_type")),
        "timestamp": normalize_frontmatter_value(metadata.get("timestamp")),
    }


def to_ordered_document_ref(document: SourceDocumentState) -> OrderedDocumentRef:
    """Project a full source document into the lighter ordering reference.

    Args:
        document: Parsed source document state.

    Returns:
        Ordered document reference persisted in durable workflow state.
    """
    return {
        "uri": document["uri"],
        "source_hash": document.get("source_hash"),
        "source_uri": document.get("source_uri"),
        "source_type": document.get("source_type"),
        "timestamp": document.get("timestamp"),
    }


def derive_source_set_key(documents: list[SourceDocumentState]) -> str:
    """Derive the stable source-set identity for a compile run.

    Args:
        documents: Parsed source documents in the current compile request.

    Returns:
        Stable ``hash-*`` or ``uri-*`` identifier for the full source set.

    Raises:
        ValueError: If the source set is empty or lacks complete hash/URI
            coverage.
    """
    if not documents:
        raise ValueError("Compile workflow requires at least one source document")

    source_hashes = [document.get("source_hash") for document in documents]
    if all(source_hashes):
        payload = "\n".join(sorted(str(value) for value in source_hashes))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"hash-{digest}"

    source_uris = [document.get("source_uri") for document in documents]
    if not any(source_hashes) and all(source_uris):
        payload = "\n".join(sorted(str(value) for value in source_uris))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"uri-{digest}"

    raise ValueError(
        "Compile workflow requires either complete source_hash coverage or complete source_uri coverage for the source set"
    )
