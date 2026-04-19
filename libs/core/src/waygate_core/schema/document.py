from uuid import uuid7
from waygate_core.schema.visibility import Visibility
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class SourceMetadataBase(BaseModel):
    model_config = ConfigDict(extra="allow")
    kind: str


class RawDocument(BaseModel):
    source_type: str
    source_id: Optional[str] = None
    source_uri: Optional[str] = None
    source_hash: Optional[str] = None
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
    source_type: str
    source_id: Optional[str] = None
    source_hash: Optional[str] = None
    source_uri: Optional[str] = None
    timestamp: Optional[datetime] = None
    topics: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
