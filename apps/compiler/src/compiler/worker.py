import logging

from compiler.graph import build_graph
from compiler import middleware
from compiler.state import GraphState
from datetime import datetime, timezone
from waygate_core.schemas import AuditEvent, AuditEventType
from compiler.config import storage


logger = logging.getLogger(__name__)


def execute_graph(initial_state: dict):
    trace_id = initial_state.get("trace_id", "unknown")
    storage.write_audit_event(
        AuditEvent(
            event_type=AuditEventType.COMPILER_WORKER_STARTED,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            trace_id=trace_id,
            document_ids=[
                entry.get("doc_id")
                for entry in initial_state.get("raw_documents_metadata", [])
                if entry.get("doc_id")
            ],
            uris=initial_state.get("new_document_uris", []),
            payload={"status": initial_state.get("status")},
        )
    )
    logger.info(
        "Executing graph trace_id=%s with initial state: %s", trace_id, initial_state
    )

    execution_state: GraphState = GraphState(**initial_state)

    middleware.ensure_default_hooks_registered()
    workflow_app = build_graph()

    final_state = workflow_app.invoke(execution_state)

    storage.write_audit_event(
        AuditEvent(
            event_type=AuditEventType.COMPILER_WORKER_COMPLETED,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            trace_id=trace_id,
            document_ids=[
                entry.get("doc_id")
                for entry in initial_state.get("raw_documents_metadata", [])
                if entry.get("doc_id")
            ],
            uris=final_state.get("new_document_uris", []),
            payload={
                "final_status": final_state.get("status"),
                "staging_uri": final_state.get("staging_uri"),
            },
        )
    )

    logger.info(
        "Graph execution completed trace_id=%s with final state: %s",
        trace_id,
        final_state,
    )

    return final_state
