from waygate_core.schema.document import DraftDocument
from typing import List, Optional

from pydantic import BaseModel, Field


class GraphStateRuntimeMetadata(BaseModel):
    """
    Runtime metadata for the compiler graph state.
    """

    trace_id: str
    enqueued_at: str


class GraphState(BaseModel):
    """
    State of the compiler graph.
    """

    # Objective of current graph execution, e.g. "compile", "publish", etc.
    task_objective: str
    # Input document URIs for the graph execution.
    source_documents: List[str]
    # Current output documents, if applicable.
    current_documents: Optional[List[DraftDocument]] = Field(default_factory=list)
    # Current revision count for the graph execution.
    revision_count: int = 0
    # Current status of the graph execution, e.g. "draft", "review", "approved", "rejected", etc.
    status: str
    # feedback from review node, if applicable.
    review_feedback: Optional[str] = None

    # Metadata about the current state of the graph execution, e.g. trace_id, enqueued_at, etc.
    runtime_metadata: GraphStateRuntimeMetadata

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
