from datetime import datetime
from enum import StrEnum
from typing import List
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class SourceType(StrEnum):
    GITHUB = "github"
    SLACK = "slack"
    WEB = "web"
    SYNTHESIS = "synthesis"
    GENERIC_WEBHOOK = "generic_webhook"
    UNKNOWN = "unknown"


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    STALE_WARNING = "stale_warning"
    ARCHIVED = "archived"
    LIVE = "live"


class Visibility(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    STRICTLY_CONFIDENTIAL = "strictly_confidential"


class SourceMetadataBase(BaseModel):
    """Base class for plugin-specific source metadata.

    All plugins **must** provide at minimum:

    - ``kind``: a short string discriminator identifying the source type
      (e.g. ``"github"``, ``"slack"``, ``"web"``).  Subclasses should
      narrow this to a ``Literal`` with a fixed default.

    Plugins may extend the base with any additional source-specific fields.
    Extra fields are allowed so the storage layer can round-trip arbitrary
    plugin metadata back as a ``SourceMetadataBase`` instance without
    knowing the concrete plugin type at load time.
    """

    model_config = ConfigDict(extra="allow")

    kind: str


class RawDocument(BaseModel):
    """A normalized representation of a single ingested item.

    Fields
    - `source_type`: logical type of the source (e.g., "slack", "github").
    - `source_id`: identifier for the source or origin of the document.
    - `timestamp`: when the event/document was produced by the source.
    - `content`: textual payload or serialized content of the document.
    - `tags`: optional list of tags to help categorize or route documents.
    - `doc_id`: globally unique identifier used for lineage and provenance.
    - `source_url`: canonical source URL when available.
    - `source_hash`: source content hash (for change detection).
    - `visibility`: visibility tag for downstream access filtering.
    - `source_metadata`: typed source-specific metadata extension block.
    """

    source_type: str
    source_id: str
    timestamp: datetime
    content: str
    tags: List[str] = Field(default_factory=list)
    doc_id: str = Field(default_factory=lambda: str(uuid4()))
    source_url: str | None = None
    source_hash: str | None = None
    visibility: Visibility = Visibility.INTERNAL
    source_metadata: SourceMetadataBase | None = None


class FrontMatterDocument(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    source_type: SourceType | str = SourceType.SYNTHESIS
    source_url: str | None = None
    source_hash: str | None = None
    status: DocumentStatus | str
    visibility: Visibility = Visibility.INTERNAL
    tags: List[str] = Field(default_factory=list)
    last_compiled: str | None = None
    lineage: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    source_metadata: SourceMetadataBase | None = None
    # Backward-compatible field that older flows still populate.
    last_updated: str | None = None
