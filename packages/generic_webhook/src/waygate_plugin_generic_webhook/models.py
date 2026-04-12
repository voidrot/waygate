from typing import Optional, List
from pydantic import BaseModel, Field


class GenericWebhookPayloadMetadata(BaseModel):
    """Metadata for the generic webhook payload."""

    event: str = Field(
        ..., description="Event type identifier (e.g. 'document.created')"
    )
    source: str = Field(..., description="Originating system or service name")
    topics: Optional[list[str]] = Field(
        default_factory=list,
        description="Optional list of topics associated with the event for routing purposes",
    )
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Optional list of tags associated with the event for filtering and search purposes",
    )
    originated_at: Optional[str] = Field(
        default=None,
        description="Optional timestamp string indicating when the event originally occurred",
    )


class GenericWebhookPayloadDocument(BaseModel):
    document_type: str = Field(..., description="Type of the document")
    document_name: Optional[str] = Field(
        default=None, description="Optional human-readable name for the document"
    )
    document_path: Optional[str] = Field(
        default=None,
        description="Optional path or URI where the document was located",
    )
    document_hash: Optional[str] = Field(
        default=None,
        description="Optional hash of the document content for integrity verification",
    )
    content: str = Field(..., description="Content of the document")
    metadata: Optional[dict] = Field(
        default_factory=dict,
        description="Optional additional metadata about the document",
    )


class GenericWebhookPayload(BaseModel):
    """Payload accepted by the generic webhook endpoint."""

    metadata: GenericWebhookPayloadMetadata = Field(
        description="Structured metadata about the webhook event"
    )
    documents: List[GenericWebhookPayloadDocument] = Field(
        default_factory=list,
        description="List of documents to process with the webhook",
    )
