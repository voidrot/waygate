from __future__ import annotations


from waygate_workflows.tools.llm import build_llm_request, resolve_llm_provider


def resolve_chat_model(workflow_name: str, fallback_model_name: str):
    provider, _ = resolve_llm_provider()
    return provider.get_llm(build_llm_request(workflow_name, fallback_model_name))


def extract_final_text(result: dict[str, object]) -> str:
    messages = result.get("messages")
    if not isinstance(messages, list) or not messages:
        return ""

    last_message = messages[-1]
    content = getattr(last_message, "content", last_message)
    if isinstance(content, list):
        return "\n".join(str(item) for item in content).strip()
    return str(content).strip()


__all__ = ["extract_final_text", "resolve_chat_model"]
