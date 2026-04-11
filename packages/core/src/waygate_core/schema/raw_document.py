from waygate_core.schema.visibility import Visibility
from uuid import uuid4
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class SourceMetadataBase(BaseModel):
    model_config = ConfigDict(extra="allow")
    kind: str


class RawDocument(BaseModel):
    source_type: str
    source_id: str
    source_url: str | None = None
    source_hash: str | None = None
    source_metadata: SourceMetadataBase | None = None
    doc_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime
    tags: List[str] = Field(default_factory=list)
    visibility: Visibility = Visibility.PUBLIC
    content: str
