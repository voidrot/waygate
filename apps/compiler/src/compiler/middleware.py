from __future__ import annotations

from collections.abc import Callable
from typing import Any

from compiler.state import GraphState

PreHook = Callable[[str, GraphState], GraphState]
PostHook = Callable[[str, GraphState, dict[str, Any]], dict[str, Any]]
NodeFunc = Callable[[GraphState], dict[str, Any]]

_pre_hooks: list[PreHook] = []
_post_hooks: list[PostHook] = []


def register_pre_hook(hook: PreHook) -> None:
    _pre_hooks.append(hook)


def register_post_hook(hook: PostHook) -> None:
    _post_hooks.append(hook)


def clear_hooks() -> None:
    _pre_hooks.clear()
    _post_hooks.clear()


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
