from __future__ import annotations

from waygate_core.plugin import WorkflowTriggerMessage
from waygate_workflows.router import process_workflow_trigger


def trigger_draft_workflow_from_message(
    message: WorkflowTriggerMessage | dict[str, object],
) -> dict[str, object]:
    """Forward an RQ-style draft trigger to the shared workflow router.

    Args:
        message: Validated trigger model or plain mapping payload.

    Returns:
        Router result describing completion, human review, or ignored status.
    """
    payload = (
        message.model_dump(mode="json")
        if isinstance(message, WorkflowTriggerMessage)
        else message
    )
    return process_workflow_trigger(payload)


__all__ = ["process_workflow_trigger", "trigger_draft_workflow_from_message"]
