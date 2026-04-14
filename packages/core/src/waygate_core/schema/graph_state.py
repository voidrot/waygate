import operator
from typing import Annotated

from pydantic import BaseModel, Field

from waygate_core.schema.document import (
    DocumentMetadataRecord,
    DraftDocument,
    DraftFragment,
    KnowledgeMetadata,
)


class DraftGraphStateRuntimeMetadata(BaseModel):
    """
    Runtime metadata for the compiler graph state.
    """

    trace_id: str
    enqueued_at: str


class DraftGraphState(BaseModel):
    """
    State of the compiler graph.
    """

    # Objective of current graph execution, e.g. "compile", "publish", etc.
    task_objective: str
    # Input document URIs for the graph execution.
    source_documents: list[str]
    # Current output documents, if applicable.
    current_documents: list[DraftDocument] = Field(default_factory=list)
    # Current revision count for the graph execution.
    revision_count: int = 0
    # Current status of the graph execution, e.g. "draft", "review", "approved", "rejected", etc.
    status: str
    # feedback from review node, if applicable.
    review_feedback: str | None = None

    topics: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    current_draft: str | None = None

    merged_metadata: KnowledgeMetadata = Field(default_factory=KnowledgeMetadata)
    document_metadata: list[DocumentMetadataRecord] = Field(default_factory=list)
    draft_fragments: list[DraftFragment] = Field(default_factory=list)
    processing_errors: list[str] = Field(default_factory=list)
    published_metadata_uri: str | None = None

    established_terms: Annotated[list[str], operator.add] = Field(default_factory=list)
    covered_topics: Annotated[list[str], operator.add] = Field(default_factory=list)
    discovered_tags: Annotated[list[str], operator.add] = Field(default_factory=list)
    final_drafts: Annotated[list[str], operator.add] = Field(default_factory=list)

    # Metadata about the current state of the graph execution, e.g. trace_id, enqueued_at, etc.
    runtime_metadata: DraftGraphStateRuntimeMetadata

    # state_version: str
    # trace_id: str
    # enqueued_at: str
    # new_document_uris: List[str]
    # raw_documents_metadata: List[dict]
    # target_topic: str
    # current_draft: Optional[str]
    # review_feedback: Optional[str]
    # staging_uri: Optional[str]
    # revision_count: int
    # status: str
    # document_type: Optional[str] = None
    # human_review_uri: Optional[str | None] = None
