"""Shared document artifact models used by storage, webhooks, and workflows."""

from datetime import datetime
from typing import Optional, List
from uuid import uuid7

from pydantic import BaseModel, Field, ConfigDict

from waygate_core.schema.visibility import Visibility


class SourceMetadataBase(BaseModel):
    """Base shape for source-specific metadata stored with a raw document."""

    model_config = ConfigDict(extra="allow")
    kind: str


class ArtifactMetadataMixin(BaseModel):
    """Shared aggregate metadata fields for non-raw document artifacts."""

    topics: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    people: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)


class SourceDocumentReference(BaseModel):
    """Normalized reference to one source document used by draft and compile artifacts."""

    uri: str
    content_hash: Optional[str] = None
    source_hash: Optional[str] = None
    source_uri: Optional[str] = None
    source_type: Optional[str] = None
    timestamp: Optional[str] = None


class RawDocument(BaseModel):
    """Canonical raw artifact produced by ingress plugins."""

    source_type: str
    source_id: Optional[str] = None
    source_uri: Optional[str] = None
    source_hash: Optional[str] = None
    content_hash: Optional[str] = None
    source_metadata: SourceMetadataBase | None = None
    doc_id: str = Field(default_factory=lambda: str(uuid7()))
    timestamp: datetime
    topics: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    people: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    project: Optional[str] = None
    organization: Optional[str] = None
    visibility: Visibility = Visibility.PUBLIC
    content: str


class RawDocumentFrontmatter(BaseModel):
    """Frontmatter subset serialized into rendered raw-document files."""

    source_type: str
    source_id: Optional[str] = None
    source_hash: Optional[str] = None
    content_hash: Optional[str] = None
    source_uri: Optional[str] = None
    timestamp: Optional[datetime] = None
    topics: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class DraftDocument(ArtifactMetadataMixin):
    """Validated compile-stage draft artifact projected from workflow state."""

    source_set_key: str
    source_documents: List[SourceDocumentReference] = Field(default_factory=list)
    review_feedback: List[str] = Field(default_factory=list)
    content: str


class CompiledDocumentFrontmatter(ArtifactMetadataMixin):
    """Frontmatter serialized into durable compiled-document artifacts."""

    doc_id: str
    source_set_key: str
    source_documents: List[str] = Field(default_factory=list)
    source_content_hashes: List[str] = Field(default_factory=list)
    source_hashes: List[str] = Field(default_factory=list)
    source_uris: List[str] = Field(default_factory=list)
    compiled_at: datetime
    review_feedback: List[str] = Field(default_factory=list)


class CompiledDocument(ArtifactMetadataMixin):
    """Durable compiled artifact written after draft review approval."""

    doc_id: str
    source_set_key: str
    source_documents: List[SourceDocumentReference] = Field(default_factory=list)
    compiled_at: datetime
    review_feedback: List[str] = Field(default_factory=list)
    content: str


class PublishedDocumentFrontmatter(ArtifactMetadataMixin):
    """Frontmatter serialized into future published-document artifacts."""

    doc_id: str
    compiled_document_ids: List[str] = Field(default_factory=list)
    compiled_document_uris: List[str] = Field(default_factory=list)
    source_set_keys: List[str] = Field(default_factory=list)
    published_at: datetime


class PublishedDocument(ArtifactMetadataMixin):
    """Future corpus-level published artifact derived from compiled documents."""

    doc_id: str
    compiled_document_ids: List[str] = Field(default_factory=list)
    compiled_document_uris: List[str] = Field(default_factory=list)
    source_set_keys: List[str] = Field(default_factory=list)
    published_at: datetime
    content: str
