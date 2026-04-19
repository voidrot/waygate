from __future__ import annotations

import json
from datetime import UTC, datetime

from waygate_workflows.schema import DraftGraphState


def build_human_review_record(state: DraftGraphState) -> str:
    record = {
        "source_set_key": state["source_set_key"],
        "raw_documents": state["raw_documents"],
        "review_feedback": state["review_feedback"],
        "current_draft": state["current_draft"],
        "resume_options": ["resume_to_synthesis", "resume_to_publish"],
        "revision_count": state["revision_count"],
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
    return json.dumps(record, indent=2, sort_keys=True)


__all__ = ["build_human_review_record"]
