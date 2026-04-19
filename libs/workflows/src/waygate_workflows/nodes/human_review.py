from __future__ import annotations

from langgraph.types import interrupt

from waygate_core.plugin import StorageNamespace

from waygate_workflows.agents.human_review import build_human_review_record
from waygate_workflows.schema import DraftGraphState, DraftWorkflowStatus
from waygate_workflows.tools.common import normalize_string_list
from waygate_workflows.utils import resolve_storage


def human_review_gate(state: DraftGraphState) -> dict[str, object]:
    source_set_key = state.get("source_set_key")
    if not source_set_key:
        raise ValueError("Human review requires a source_set_key")

    storage = resolve_storage()
    review_path = storage.build_namespaced_path(
        StorageNamespace.Review,
        f"{source_set_key}.json",
    )
    review_uri = storage.write_document(review_path, build_human_review_record(state))
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
        raise ValueError("Human review resume payload must be a mapping")

    action = str(decision.get("action", "")).strip()
    if action not in {"resume_to_synthesis", "resume_to_publish"}:
        raise ValueError(
            "Human review action must be 'resume_to_synthesis' or 'resume_to_publish'"
        )

    feedback = normalize_string_list(decision.get("feedback"))
    combined_feedback = normalize_string_list([*state["review_feedback"], *feedback])
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
    if state.get("human_review_action") == "resume_to_publish":
        return "publish"
    return "synthesis"
