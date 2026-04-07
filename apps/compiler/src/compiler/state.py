from typing import List, Optional, TypedDict
from typing_extensions import NotRequired


class GraphState(TypedDict):
    state_version: str
    trace_id: str
    enqueued_at: str
    new_document_uris: List[str]
    # Each entry is a RawDocument serialised via model_dump(mode="json") so the
    # state passes cleanly through RQ (pickle) and JSON checkpointers alike.
    raw_documents_metadata: List[dict]
    target_topic: str
    document_type: NotRequired[str]
    template_name: NotRequired[str]
    current_draft: Optional[str]
    qa_feedback: Optional[str]
    staging_uri: Optional[str]
    revision_count: int
    status: str
