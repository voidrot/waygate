from __future__ import annotations

import json
from datetime import UTC, datetime

from waygate_core.logging import get_logger

from waygate_workflows.schema import DraftGraphState

logger = get_logger(__name__)


def build_human_review_record(state: DraftGraphState) -> str:
    """Build the persisted human-review artifact for an interrupted draft.

    Args:
        state: Draft workflow state at the human-review boundary.

    Returns:
        JSON record written to review storage for operator handling.
    """
    logger.debug(
        "Building human review record",
        source_set_key=state.get("source_set_key"),
        revision_count=state["revision_count"],
        raw_document_count=len(state["raw_documents"]),
        feedback_count=len(state["review_feedback"]),
    )
    record = {
        "source_set_key": state["source_set_key"],
        "raw_documents": state["raw_documents"],
        "review_feedback": state["review_feedback"],
        "current_draft": state["current_draft"],
        "resume_options": ["resume_to_synthesis", "resume_to_publish"],
        "revision_count": state["revision_count"],
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
    rendered = json.dumps(record, indent=2, sort_keys=True)
    logger.debug(
        "Built human review record",
        source_set_key=state.get("source_set_key"),
        record_length=len(rendered),
    )
    return rendered


__all__ = ["build_human_review_record"]
