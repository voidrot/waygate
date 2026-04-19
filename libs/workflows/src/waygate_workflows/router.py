from __future__ import annotations

import hashlib
import json

from langgraph.checkpoint.postgres import PostgresSaver

from waygate_core.logging import get_logger
from waygate_core.plugin import WorkflowTriggerMessage

from waygate_workflows.schema import DraftGraphState
from waygate_workflows.schema import DraftWorkflowStatus
from waygate_workflows.schema import WorkflowEvent
from waygate_workflows.schema import WorkflowType
from waygate_workflows.tools.checkpoint import build_postgres_connection_string
from waygate_workflows.workflows.compile import compile_workflow

logger = get_logger(__name__)


def _build_thread_id(message: WorkflowTriggerMessage) -> str:
    if message.idempotency_key:
        return f"compile:{message.idempotency_key}"

    payload = "\n".join(sorted(message.document_paths))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"compile:{digest}"


def _build_initial_state(message: WorkflowTriggerMessage) -> DraftGraphState:
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
        "published_document_uri": None,
        "published_document_id": None,
        "human_review_record_uri": None,
        "human_review_action": None,
    }


def _invoke_compile_workflow(
    message: WorkflowTriggerMessage,
) -> tuple[str, dict[str, object]]:
    thread_id = _build_thread_id(message)
    config = {"configurable": {"thread_id": thread_id}}
    with PostgresSaver.from_conn_string(build_postgres_connection_string()) as saver:
        saver.setup()
        workflow = compile_workflow(checkpointer=saver)
        result = workflow.invoke(_build_initial_state(message), config=config)
    return thread_id, result


def process_workflow_trigger(payload: dict | str) -> dict[str, object]:
    """Process a workflow trigger payload from a worker runtime."""
    logger.info("Received workflow trigger", payload=payload)

    raw_payload = json.loads(payload) if isinstance(payload, str) else payload
    message = WorkflowTriggerMessage.model_validate(raw_payload)
    event_type = message.event_type

    match event_type:
        case WorkflowEvent.DRAFT_READY.value:
            logger.info(
                "Processing draft.ready workflow trigger",
                source=message.source,
            )
            thread_id, result = _invoke_compile_workflow(message)
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

            return {
                "status": "completed",
                "request_key": thread_id,
                "document_paths": message.document_paths,
                "metadata": message.metadata,
                "source_set_key": result.get("source_set_key"),
                "published_document_uri": result.get("published_document_uri"),
                "published_document_id": result.get("published_document_id"),
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
