from typing import Any

from pydantic import BaseModel, Field


class GenericWebhookPayloadMetadata(BaseModel):
    """Metadata for a generic webhook event."""

    event: str = Field(
        ...,
        description="Event type identifier (for example, 'document.created').",
    )
    source: str = Field(..., description="Originating system or service name.")
    topics: list[str] = Field(
        default_factory=list,
        description="Optional topics associated with the webhook event.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional tags associated with the webhook event.",
    )
    originated_at: str | None = Field(
        default=None,
        description="Optional ISO-8601 timestamp for when the event occurred.",
    )


class GenericWebhookPayloadDocument(BaseModel):
    document_type: str = Field(..., description="Type of document in the payload.")
    document_name: str | None = Field(
        default=None,
        description="Optional human-readable name of the document.",
    )
    document_path: str | None = Field(
        default=None,
        description="Optional source path or URI of the document.",
    )
    document_hash: str | None = Field(
        default=None,
        description="Optional content hash for integrity checks.",
    )
    content: str = Field(..., description="Document content.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional document-level metadata, including topics and tags.",
    )


class GenericWebhookPayload(BaseModel):
    """Payload accepted by the generic webhook endpoint."""

    metadata: GenericWebhookPayloadMetadata = Field(
        description="Structured metadata describing the webhook event."
    )
    documents: list[GenericWebhookPayloadDocument] = Field(
        default_factory=list,
        description="Documents emitted by the webhook event.",
    )
