from __future__ import annotations

import re

from waygate_core.plugin import StorageNamespace

from waygate_workflows.utils import resolve_storage


def _normalize_source_type_slug(source_type: str) -> str:
    """Normalize a source type into the storage slug used for guidance docs.

    Args:
        source_type: Source-type label discovered from raw document metadata.

    Returns:
        Lowercase hyphenated slug safe for storage path construction.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", source_type.strip().lower())
    return slug.strip("-")


def _read_optional_guidance(document_path: str) -> str | None:
    """Read optional agent guidance text from storage.

    Args:
        document_path: Relative path under the ``agents`` storage namespace.

    Returns:
        Trimmed guidance text when present, otherwise ``None``.
    """
    try:
        storage = resolve_storage()
    except Exception:
        return None

    namespaced_path = storage.build_namespaced_path(
        StorageNamespace.Agents,
        document_path,
    )
    try:
        content = storage.read_document(namespaced_path).strip()
    except FileNotFoundError, KeyError:
        return None
    return content or None


def load_agent_guidance_instructions(
    *,
    workflow_name: str,
    role_name: str,
    source_type: str | None = None,
) -> list[str]:
    """Load guidance snippets for a workflow role.

    Args:
        workflow_name: Workflow identifier such as ``compile``.
        role_name: Agent role identifier such as ``source-analysis``.
        source_type: Optional source-type discriminator for specialized
            guidance.

    Returns:
        Ordered list of guidance snippets to append to prompt instructions.
    """
    instructions: list[str] = []

    common_guidance = _read_optional_guidance(f"{workflow_name}/{role_name}/common.md")
    if common_guidance:
        instructions.append(common_guidance)

    if source_type:
        source_type_slug = _normalize_source_type_slug(source_type)
        if source_type_slug:
            source_guidance = _read_optional_guidance(
                f"{workflow_name}/{role_name}/source-types/{source_type_slug}.md"
            )
            if source_guidance:
                instructions.append(source_guidance)

    return instructions


__all__ = ["load_agent_guidance_instructions"]
