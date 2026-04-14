from waygate_core.schema.visibility import Visibility
from datetime import datetime
from typing import List, Optional
from uuid_utils import uuid4
from pydantic import BaseModel, Field, ConfigDict


class KnowledgeMetadata(BaseModel):
    topics: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    people: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    established_terms: List[str] = Field(default_factory=list)


class MetadataExtractionResult(KnowledgeMetadata):
    summary: str | None = None


class DocumentMetadataRecord(MetadataExtractionResult):
    source_document: str
    source_type: str = "unknown"
    source_id: str | None = None
    source_uri: str | None = None
    source_hash: str | None = None


class DraftGenerationResult(BaseModel):
    content: str
    summary: str | None = None


class DraftMergeResult(BaseModel):
    content: str


class DraftFragment(BaseModel):
    source_document: str
    content: str
    summary: str | None = None
    topics: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    people: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)


class DraftDocument(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    file_name: str | None = None
    topics: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    people: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    project: Optional[str] = None
    organization: Optional[str] = None


class RawDocument(BaseModel):
    source_type: str
    source_id: Optional[str] = None
    source_uri: Optional[str] = None
    source_hash: Optional[str] = None
    source_metadata: SourceMetadataBase | None = None
    doc_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime
    topics: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    visibility: Visibility = Visibility.PUBLIC
    content: str


class SourceMetadataBase(BaseModel):
    model_config = ConfigDict(extra="allow")
    kind: str
