from __future__ import annotations

import asyncio
import hashlib
import json

from langgraph.checkpoint.postgres import PostgresSaver

from waygate_core import get_app_context
from waygate_core.logging import get_logger
from waygate_core.plugin import (
    DispatchErrorKind,
    LLMConfigurationError,
    WorkflowDispatchResult,
    WorkflowTriggerMessage,
    resolve_communication_client,
)

from waygate_workflows.schema import DraftGraphState
from waygate_workflows.schema import DraftWorkflowStatus
from waygate_workflows.schema import WorkflowEvent
from waygate_workflows.schema import WorkflowType
from waygate_workflows.runtime.checkpoint import build_postgres_connection_string
from waygate_workflows.workflows.compile import compile_workflow

logger = get_logger(__name__)


def _build_thread_id(message: WorkflowTriggerMessage) -> str:
    """Build a stable LangGraph thread id for a workflow trigger.

    Args:
        message: Validated workflow trigger payload.

    Returns:
        Deterministic thread id derived from the idempotency key when present,
        otherwise from the sorted document path set.
    """
    if message.idempotency_key:
        return f"compile:{message.idempotency_key}"

    payload = "\n".join(sorted(message.document_paths))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"compile:{digest}"


def _build_initial_state(message: WorkflowTriggerMessage) -> DraftGraphState:
    """Construct the initial compile graph state from a trigger message.

    Args:
        message: Validated workflow trigger payload.

    Returns:
        Fresh graph state ready for the compile workflow entrypoint.
    """
    return {
        "workflow_type": WorkflowType.DRAFT,
        "event_type": WorkflowEvent.DRAFT_READY,
        "source": message.source,
        "raw_documents": message.document_paths,
        "source_documents": [],
        "document_order": [],
        "document_cursor": 0,
        "active_document": None,
        "source_set_key": None,
        "revision_count": 0,
        "status": DraftWorkflowStatus.READY,
        "scratchpad": {"terms": [], "claims": []},
        "extracted_metadata": [],
        "document_summaries": [],
        "prior_document_briefs": [],
        "canonical_topics": [],
        "canonical_tags": [],
        "glossary": [],
        "entity_registry": [],
        "claim_ledger": [],
        "reference_index": [],
        "unresolved_mentions": [],
        "current_draft": "",
        "review_feedback": [],
        "review_outcome": None,
        "compiled_document_uri": None,
        "compiled_document_id": None,
        "compiled_document_hash": None,
        "human_review_record_uri": None,
        "human_review_action": None,
    }


def _dispatch_integration_trigger(
    parent_message: WorkflowTriggerMessage,
    result: dict[str, object],
) -> WorkflowDispatchResult | None:
    """Dispatch the follow-on ready.integrate trigger for a compiled artifact."""

    compiled_document_uri = result.get("compiled_document_uri")
    compiled_document_id = result.get("compiled_document_id")
    compiled_document_hash = result.get("compiled_document_hash")
    if not isinstance(compiled_document_uri, str) or not isinstance(
        compiled_document_id, str
    ):
        return None

    metadata = dict(parent_message.metadata)
    source_set_key = result.get("source_set_key")
    if source_set_key is not None:
        metadata["source_set_key"] = str(source_set_key)
    metadata["compiled_document_id"] = compiled_document_id
    metadata["compiled_document_hash"] = str(
        compiled_document_hash or compiled_document_id
    )

    trigger = WorkflowTriggerMessage(
        event_type=WorkflowEvent.READY_INTEGRATE.value,
        source="waygate-workflows.compile",
        document_paths=[compiled_document_uri],
        idempotency_key=compiled_document_id,
        metadata=metadata,
    )

    try:
        app_context = get_app_context()
        client = resolve_communication_client(
            app_context.plugins.communication,
            app_context.config.core.communication_plugin_name,
            allow_fallback=False,
        )
        return asyncio.run(client.submit_workflow_trigger(trigger))
    except Exception as exc:
        return WorkflowDispatchResult(
            accepted=False,
            detail=f"Failed to dispatch ready.integrate trigger: {exc}",
            error_kind=DispatchErrorKind.CONFIG,
        )


def _invoke_compile_workflow(
    message: WorkflowTriggerMessage,
) -> tuple[str, dict[str, object]]:
    """Run the compile workflow for one trigger message.

    Args:
        message: Validated workflow trigger payload.

    Returns:
        Tuple of the workflow thread id and the final workflow state snapshot.
    """
    thread_id = _build_thread_id(message)
    config = {"configurable": {"thread_id": thread_id}}
    with PostgresSaver.from_conn_string(build_postgres_connection_string()) as saver:
        saver.setup()
        workflow = compile_workflow(checkpointer=saver)
        result = workflow.invoke(_build_initial_state(message), config=config)
    return thread_id, result


def process_workflow_trigger(payload: dict | str) -> dict[str, object]:
    """Process a workflow trigger payload from a worker runtime.

    Args:
        payload: Raw trigger payload as a mapping or serialized JSON string.

    Returns:
        Transport-friendly result describing completion, human review, or an
        ignored event.
    """
    logger.info("Received workflow trigger", payload=payload)

    raw_payload = json.loads(payload) if isinstance(payload, str) else payload
    message = WorkflowTriggerMessage.model_validate(raw_payload)
    event_type = message.event_type

    match event_type:
        case WorkflowEvent.DRAFT_READY.value:
            thread_id = _build_thread_id(message)
            if not message.document_paths:
                detail = "draft.ready requires at least one document path"
                logger.error(
                    "Rejecting draft.ready workflow trigger with no documents",
                    source=message.source,
                    request_key=thread_id,
                    detail=detail,
                )
                return {
                    "status": "failed",
                    "error_kind": DispatchErrorKind.VALIDATION.value,
                    "detail": detail,
                    "request_key": thread_id,
                    "event_type": event_type,
                    "document_paths": message.document_paths,
                    "metadata": message.metadata,
                }

            logger.info(
                "Processing draft.ready workflow trigger",
                source=message.source,
            )
            try:
                thread_id, result = _invoke_compile_workflow(message)
            except LLMConfigurationError as exc:
                logger.error(
                    "Compile workflow configuration failed",
                    source=message.source,
                    request_key=thread_id,
                    detail=str(exc),
                )
                return {
                    "status": "failed",
                    "error_kind": DispatchErrorKind.CONFIG.value,
                    "detail": str(exc),
                    "request_key": thread_id,
                    "event_type": event_type,
                    "document_paths": message.document_paths,
                    "metadata": message.metadata,
                }
            if "__interrupt__" in result:
                return {
                    "status": "human_review",
                    "request_key": thread_id,
                    "document_paths": message.document_paths,
                    "metadata": message.metadata,
                    "source_set_key": result.get("source_set_key"),
                    "human_review_record_uri": result.get("human_review_record_uri"),
                    "interrupts": result["__interrupt__"],
                }

            dispatch_result = _dispatch_integration_trigger(message, result)
            if dispatch_result is not None and not dispatch_result.accepted:
                return {
                    "status": "failed",
                    "error_kind": (
                        dispatch_result.error_kind.value
                        if dispatch_result.error_kind is not None
                        else DispatchErrorKind.PERMANENT.value
                    ),
                    "detail": dispatch_result.detail,
                    "request_key": thread_id,
                    "event_type": event_type,
                    "document_paths": message.document_paths,
                    "metadata": message.metadata,
                    "source_set_key": result.get("source_set_key"),
                    "compiled_document_uri": result.get("compiled_document_uri"),
                    "compiled_document_id": result.get("compiled_document_id"),
                    "compiled_document_hash": result.get("compiled_document_hash"),
                }

            return {
                "status": "completed",
                "request_key": thread_id,
                "document_paths": message.document_paths,
                "metadata": message.metadata,
                "source_set_key": result.get("source_set_key"),
                "compiled_document_uri": result.get("compiled_document_uri"),
                "compiled_document_id": result.get("compiled_document_id"),
                "compiled_document_hash": result.get("compiled_document_hash"),
            }
        case WorkflowEvent.READY_INTEGRATE.value:
            logger.info(
                "Ignoring deferred ready.integrate workflow trigger",
                source=message.source,
                document_paths=message.document_paths,
            )
            return {
                "status": "ignored",
                "event_type": event_type,
                "document_paths": message.document_paths,
                "metadata": message.metadata,
            }
        case _:
            logger.error(
                "Ignoring unsupported workflow trigger event",
                event_type=event_type,
                source=message.source,
            )
            return {
                "status": "ignored",
                "event_type": event_type,
                "document_paths": message.document_paths,
                "metadata": message.metadata,
            }
