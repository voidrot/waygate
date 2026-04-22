"""Shared document schemas used across WayGate packages."""

from .document import (
    CompiledDocument,
    CompiledDocumentFrontmatter,
    DraftDocument,
    PublishedDocument,
    PublishedDocumentFrontmatter,
    RawDocument,
    RawDocumentFrontmatter,
    SourceDocumentReference,
    SourceMetadataBase,
)
from .visibility import Visibility

__all__ = [
    "CompiledDocument",
    "CompiledDocumentFrontmatter",
    "DraftDocument",
    "PublishedDocument",
    "PublishedDocumentFrontmatter",
    "RawDocument",
    "RawDocumentFrontmatter",
    "SourceDocumentReference",
    "SourceMetadataBase",
    "Visibility",
]
