from __future__ import annotations

from waygate_core.plugin import WorkflowTriggerMessage
from waygate_workflows.router import process_workflow_trigger


def trigger_draft_workflow_from_message(
    message: WorkflowTriggerMessage | dict[str, object],
) -> dict[str, object]:
    payload = (
        message.model_dump(mode="json")
        if isinstance(message, WorkflowTriggerMessage)
        else message
    )
    return process_workflow_trigger(payload)


__all__ = ["process_workflow_trigger", "trigger_draft_workflow_from_message"]
