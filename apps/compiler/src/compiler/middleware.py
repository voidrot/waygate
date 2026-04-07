from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Callable
from typing import Any

from compiler.state import GraphState
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
    _emit_audit_event(
        AuditEvent(
            event_type=AuditEventType.COMPILER_NODE_STARTED,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            trace_id=state.get("trace_id"),
            document_ids=[
                entry.get("doc_id")
                for entry in state.get("raw_documents_metadata", [])
                if entry.get("doc_id")
            ],
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
    _emit_audit_event(
        AuditEvent(
            event_type=AuditEventType.COMPILER_NODE_COMPLETED,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            trace_id=state.get("trace_id"),
            document_ids=[
                entry.get("doc_id")
                for entry in state.get("raw_documents_metadata", [])
                if entry.get("doc_id")
            ],
            uris=state.get("new_document_uris", []),
            payload={
                "node_name": node_name,
                "result_status": result.get("status"),
                "staging_uri": result.get("staging_uri"),
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
        current_state = state
        for hook in _pre_hooks:
            current_state = hook(node_name, current_state)

        result = node_fn(current_state)

        current_result = result
        for hook in _post_hooks:
            current_result = hook(node_name, current_state, current_result)

        return current_result

    return wrapped
