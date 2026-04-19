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
