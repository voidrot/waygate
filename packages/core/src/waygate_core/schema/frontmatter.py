from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class RawDocumentFrontmatter(BaseModel):
    source_type: str
    source_id: Optional[str] = None
    source_hash: Optional[str] = None
    source_uri: Optional[str] = None
    timestamp: Optional[datetime] = None
    topics: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
