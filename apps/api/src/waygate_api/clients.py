from waygate_core import get_app_context
from waygate_core.plugin import (
    CommunicationClientPlugin,
    WorkflowDispatchResult,
    WorkflowTriggerMessage,
    resolve_communication_client,
)


def _resolve_communication_client() -> CommunicationClientPlugin:
    """Resolve the configured communication client from the app context.

    Returns:
        The selected communication client plugin.
    """

    app_context = get_app_context()
    return resolve_communication_client(
        app_context.plugins.communication,
        app_context.config.core.communication_plugin_name,
        allow_fallback=False,
    )


async def send_draft_message(document_paths: list[str]) -> WorkflowDispatchResult:
    """Submit a draft-ready workflow trigger for the given document paths.

    Args:
        document_paths: Storage-backed document paths to include in the trigger.

    Returns:
        The dispatch result returned by the communication client.
    """

    if not document_paths:
        return WorkflowDispatchResult(
            accepted=True, detail="No document paths supplied"
        )

    message = WorkflowTriggerMessage(
        event_type="draft.ready",
        source="waygate-api.webhooks",
        document_paths=document_paths,
    )
    return await send_workflow_message(message)


async def send_workflow_message(
    message: WorkflowTriggerMessage,
) -> WorkflowDispatchResult:
    """Submit an arbitrary workflow trigger via the configured transport.

    Args:
        message: The workflow trigger message to submit.

    Returns:
        The dispatch result returned by the communication client.
    """

    client = _resolve_communication_client()
    return await client.submit_workflow_trigger(message)
