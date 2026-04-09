from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Callable
from typing import Any

from compiler.state import GraphState
from waygate_core.observability import start_span
from waygate_core.schemas import AuditEvent, AuditEventType

PreHook = Callable[[str, GraphState], GraphState]
PostHook = Callable[[str, GraphState, dict[str, Any]], dict[str, Any]]
NodeFunc = Callable[[GraphState], dict[str, Any]]

_pre_hooks: list[PreHook] = []
_post_hooks: list[PostHook] = []
_default_hooks_registered = False


def register_pre_hook(hook: PreHook) -> None:
    _pre_hooks.append(hook)


def register_post_hook(hook: PostHook) -> None:
    _post_hooks.append(hook)


def clear_hooks() -> None:
    global _default_hooks_registered
    _pre_hooks.clear()
    _post_hooks.clear()
    _default_hooks_registered = False


def _emit_audit_event(event: AuditEvent) -> None:
    from compiler.config import storage

    storage.write_audit_event(event)


def _audit_pre_hook(node_name: str, state: GraphState) -> GraphState:
    document_ids = [
        str(entry["doc_id"])
        for entry in state.get("raw_documents_metadata", [])
        if isinstance(entry, dict) and entry.get("doc_id")
    ]

    _emit_audit_event(
        AuditEvent(
            event_type=AuditEventType.COMPILER_NODE_STARTED,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            trace_id=state.get("trace_id"),
            document_ids=document_ids,
            uris=state.get("new_document_uris", []),
            payload={
                "node_name": node_name,
                "revision_count": state.get("revision_count", 0),
                "status": state.get("status"),
            },
        )
    )
    return state


def _audit_post_hook(
    node_name: str,
    state: GraphState,
    result: dict[str, Any],
) -> dict[str, Any]:
    document_ids = [
        str(entry["doc_id"])
        for entry in state.get("raw_documents_metadata", [])
        if isinstance(entry, dict) and entry.get("doc_id")
    ]

    _emit_audit_event(
        AuditEvent(
            event_type=AuditEventType.COMPILER_NODE_COMPLETED,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            trace_id=state.get("trace_id"),
            document_ids=document_ids,
            uris=state.get("new_document_uris", []),
            payload={
                "node_name": node_name,
                "result_status": result.get("status"),
                "staging_uri": result.get("staging_uri"),
                "human_review_uri": result.get("human_review_uri"),
            },
        )
    )
    return result


def ensure_default_hooks_registered() -> None:
    global _default_hooks_registered
    if _default_hooks_registered:
        return

    register_pre_hook(_audit_pre_hook)
    register_post_hook(_audit_post_hook)
    _default_hooks_registered = True


def apply_hooks(node_name: str, node_fn: NodeFunc) -> NodeFunc:
    def wrapped(state: GraphState) -> dict[str, Any]:
        with start_span(
            f"compiler.node.{node_name}",
            tracer_name=__name__,
            attributes={
                "waygate.node_name": node_name,
                "waygate.trace_id": state.get("trace_id"),
                "waygate.revision_count": state.get("revision_count", 0),
                "waygate.status": state.get("status"),
            },
        ) as span:
            current_state = state
            for hook in _pre_hooks:
                current_state = hook(node_name, current_state)

            result = node_fn(current_state)

            current_result = result
            for hook in _post_hooks:
                current_result = hook(node_name, current_state, current_result)

            result_status = current_result.get("status")
            if isinstance(result_status, str):
                span.set_attribute("waygate.result_status", result_status)

            staging_uri = current_result.get("staging_uri")
            if isinstance(staging_uri, str):
                span.set_attribute("waygate.staging_uri", staging_uri)

            human_review_uri = current_result.get("human_review_uri")
            if isinstance(human_review_uri, str):
                span.set_attribute(
                    "waygate.human_review_uri",
                    human_review_uri,
                )

            return current_result

    return wrapped
