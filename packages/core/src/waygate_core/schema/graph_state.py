from typing import List, NotRequired, Optional, TypedDict


class GraphState(TypedDict):
    """
    State of the compiler graph.
    """

    state_version: str
    trace_id: str
    enqueued_at: str
    new_document_uris: List[str]
    raw_documents_metadata: List[dict]
    target_topic: str
    document_type: NotRequired[str]
    current_draft: Optional[str]
    review_feedback: Optional[str]
    staging_uri: Optional[str]
    human_review_uri: NotRequired[str | None]
    revision_count: int
    status: str
