from typing import List, Optional, TypedDict


class GraphState(TypedDict):
    new_document_uris: List[str]
    target_topic: str
    current_draft: Optional[str]
    qa_feedback: Optional[str]
    revision_count: int
    status: str
