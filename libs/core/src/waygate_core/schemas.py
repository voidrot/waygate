from datetime import datetime
from typing import List

from pydantic import BaseModel


class RawDocument(BaseModel):
    """A normalized representation of a single ingested item.

    Fields
    - `source_type`: logical type of the source (e.g., "slack", "github").
    - `source_id`: identifier for the source or origin of the document.
    - `timestamp`: when the event/document was produced by the source.
    - `content`: textual payload or serialized content of the document.
    - `tags`: optional list of tags to help categorize or route documents.
    """

    source_type: str
    source_id: str
    timestamp: datetime
    content: str
    tags: List[str] = []


class FrontMatterDocument(BaseModel):
    title: str
    last_updated: str
    status: str
    tags: List[str] = []
    sources: List[str] = []
