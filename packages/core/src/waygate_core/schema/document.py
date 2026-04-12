from waygate_core.schema.visibility import Visibility
from datetime import datetime
from typing import List, Optional
from uuid_utils import uuid4
from pydantic import BaseModel, Field, ConfigDict


class DraftDocument(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    file_name: str | None = None
    topics: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
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
