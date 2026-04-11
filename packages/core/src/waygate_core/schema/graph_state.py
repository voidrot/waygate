from typing import List, Optional
from dataclasses import dataclass


@dataclass
class GraphState:
    """
    State of the compiler graph.
    """

    state_version: str
    trace_id: str
    enqueued_at: str
    new_document_uris: List[str]
    raw_documents_metadata: List[dict]
    target_topic: str
    current_draft: Optional[str]
    review_feedback: Optional[str]
    staging_uri: Optional[str]
    revision_count: int
    status: str
    document_type: Optional[str] = None
    human_review_uri: Optional[str | None] = None
