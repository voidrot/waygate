"""Document template rendering helpers used by the compile workflow."""

from .template import (
    build_compiled_document_frontmatter,
    build_published_document_frontmatter,
    compute_content_hash,
    infer_content_type,
    normalize_content_type,
    normalize_document_body,
    build_raw_document_frontmatter,
    render_compiled_document,
    render_published_document,
    render_raw_document,
)

__all__ = [
    "build_compiled_document_frontmatter",
    "build_published_document_frontmatter",
    "compute_content_hash",
    "infer_content_type",
    "normalize_content_type",
    "normalize_document_body",
    "build_raw_document_frontmatter",
    "render_compiled_document",
    "render_published_document",
    "render_raw_document",
]
