from __future__ import annotations


def normalize_string_list(values: object) -> list[str]:
    """Normalize arbitrary input into a deduplicated list of non-empty strings.

    Args:
        values: Scalar value, list-like value, or ``None``.

    Returns:
        Deduplicated string values in first-seen order.
    """
    if values is None:
        return []

    candidates = values if isinstance(values, list) else [values]
    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        text = str(candidate).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


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
