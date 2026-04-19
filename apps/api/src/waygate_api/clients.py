from waygate_core import get_app_context
from waygate_core.plugin import (
    CommunicationClientPlugin,
    WorkflowDispatchResult,
    WorkflowTriggerMessage,
    resolve_communication_client,
)


def _resolve_communication_client() -> CommunicationClientPlugin:
    app_context = get_app_context()
    return resolve_communication_client(
        app_context.plugins.communication,
        app_context.config.core.communication_plugin_name,
        allow_fallback=False,
    )


async def send_draft_message(document_paths: list[str]) -> WorkflowDispatchResult:
    if not document_paths:
        return WorkflowDispatchResult(
            accepted=True, detail="No document paths supplied"
        )

    client = _resolve_communication_client()
    message = WorkflowTriggerMessage(
        event_type="draft.ready",
        source="waygate-api.webhooks",
        document_paths=document_paths,
    )
    return await client.submit_workflow_trigger(message)
