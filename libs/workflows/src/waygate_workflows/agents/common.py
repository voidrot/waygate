from __future__ import annotations


from waygate_workflows.tools.llm import (
    build_llm_request,
    resolve_llm_provider,
    validate_llm_request,
)


def resolve_chat_model(
    workflow_name: str,
    fallback_model_name: str,
    *,
    target_name: str | None = None,
    requires_structured_output: bool = False,
):
    """Resolve a chat-capable model runnable for one workflow stage.

    Args:
        workflow_name: Logical workflow or stage name.
        fallback_model_name: Default model name when no workflow profile exists.
        target_name: Optional exact role or target identifier.
        requires_structured_output: Whether the caller requires structured
            output support from the provider.

    Returns:
        Provider-specific runnable returned by the configured LLM plugin.
    """
    provider, core_settings = resolve_llm_provider()
    request = build_llm_request(
        workflow_name,
        fallback_model_name,
        target_name=target_name,
        core_settings=core_settings,
    )
    validate_llm_request(
        provider,
        request,
        requires_structured_output=requires_structured_output,
    )
    return provider.get_llm(request)


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
