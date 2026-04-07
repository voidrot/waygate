from typing import List, Optional, TypedDict


class GraphState(TypedDict):
    new_document_uris: List[str]
    # Each entry is a RawDocument serialised via model_dump(mode="json") so the
    # state passes cleanly through RQ (pickle) and JSON checkpointers alike.
    raw_documents_metadata: List[dict]
    target_topic: str
    current_draft: Optional[str]
    qa_feedback: Optional[str]
    revision_count: int
    status: str
