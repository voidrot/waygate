from __future__ import annotations

from langgraph.types import interrupt

from waygate_core.logging import get_logger
from waygate_core.plugin import StorageNamespace

from waygate_workflows.agents.human_review import build_human_review_record
from waygate_workflows.runtime.storage import resolve_storage
from waygate_workflows.runtime.text import normalize_string_list
from waygate_workflows.schema import DraftGraphState, DraftWorkflowStatus

logger = get_logger(__name__)


def human_review_gate(state: DraftGraphState) -> dict[str, object]:
    """Persist a human-review record and interrupt the workflow.

    Args:
        state: Draft workflow state at the human-review boundary.

    Returns:
        Partial state update containing the persisted review artifact and the
        chosen resume action.

    Raises:
        ValueError: If the source-set key is missing or the resume payload is
            invalid.
    """
    source_set_key = state.get("source_set_key")
    if not source_set_key:
        logger.error(
            "Human review requires a source_set_key",
            revision_count=state.get("revision_count"),
        )
        raise ValueError("Human review requires a source_set_key")

    logger.info(
        "Creating human review interrupt",
        source_set_key=source_set_key,
        revision_count=state["revision_count"],
        feedback_count=len(state["review_feedback"]),
    )
    storage = resolve_storage()
    review_path = storage.build_namespaced_path(
        StorageNamespace.Review,
        f"{source_set_key}.json",
    )
    review_uri = storage.write_document(review_path, build_human_review_record(state))
    logger.info(
        "Persisted human review record",
        source_set_key=source_set_key,
        human_review_record_uri=review_uri,
    )
    # LangGraph returns the resume payload here when a human resumes the run.
    decision = interrupt(
        {
            "type": "compile_human_review",
            "source_set_key": source_set_key,
            "review_feedback": state["review_feedback"],
            "current_draft": state["current_draft"],
            "resume_options": ["resume_to_synthesis", "resume_to_publish"],
            "human_review_record_uri": review_uri,
        }
    )
    if not isinstance(decision, dict):
        logger.error(
            "Human review resume payload must be a mapping",
            source_set_key=source_set_key,
            payload_type=type(decision).__name__,
        )
        raise ValueError("Human review resume payload must be a mapping")

    action = str(decision.get("action", "")).strip()
    if action not in {"resume_to_synthesis", "resume_to_publish"}:
        logger.error(
            "Human review action was invalid",
            source_set_key=source_set_key,
            action=action,
        )
        raise ValueError(
            "Human review action must be 'resume_to_synthesis' or 'resume_to_publish'"
        )

    feedback = normalize_string_list(decision.get("feedback"))
    combined_feedback = normalize_string_list([*state["review_feedback"], *feedback])
    logger.info(
        "Human review resumed workflow",
        source_set_key=source_set_key,
        action=action,
        added_feedback_count=len(feedback),
        total_feedback_count=len(combined_feedback),
    )
    return {
        "human_review_record_uri": review_uri,
        "human_review_action": action,
        "review_feedback": combined_feedback,
        "status": (
            DraftWorkflowStatus.APPROVED
            if action == "resume_to_publish"
            else DraftWorkflowStatus.REJECTED
        ),
    }


def route_human_review(state: DraftGraphState) -> str:
    """Choose the next node after a human-review resume decision.

    Args:
        state: Current draft workflow state after the human-review interrupt.

    Returns:
        ``publish`` when the operator approves publication, otherwise
        ``synthesis`` to revise the draft.
    """
    if state.get("human_review_action") == "resume_to_publish":
        logger.info(
            "Routing human-approved draft to publish",
            source_set_key=state.get("source_set_key"),
        )
        return "publish"
    logger.info(
        "Routing human-reviewed draft back to synthesis",
        source_set_key=state.get("source_set_key"),
        action=state.get("human_review_action"),
    )
    return "synthesis"
