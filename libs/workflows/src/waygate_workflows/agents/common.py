from __future__ import annotations


from waygate_workflows.tools.llm import build_llm_request, resolve_llm_provider


def resolve_chat_model(workflow_name: str, fallback_model_name: str):
    """Resolve a chat-capable model runnable for one workflow stage.

    Args:
        workflow_name: Logical workflow or stage name.
        fallback_model_name: Default model name when no workflow profile exists.

    Returns:
        Provider-specific runnable returned by the configured LLM plugin.
    """
    provider, _ = resolve_llm_provider()
    return provider.get_llm(build_llm_request(workflow_name, fallback_model_name))


def extract_final_text(result: dict[str, object]) -> str:
    """Extract final text content from a LangChain agent response.

    Args:
        result: Agent invocation result containing a ``messages`` sequence.

    Returns:
        Trimmed final text content, or an empty string when no messages exist.
    """
    messages = result.get("messages")
    if not isinstance(messages, list) or not messages:
        return ""

    last_message = messages[-1]
    content = getattr(last_message, "content", last_message)
    if isinstance(content, list):
        return "\n".join(str(item) for item in content).strip()
    return str(content).strip()


__all__ = ["extract_final_text", "resolve_chat_model"]
