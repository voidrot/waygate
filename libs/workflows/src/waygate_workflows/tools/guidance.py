from __future__ import annotations

import re

from waygate_core.plugin import StorageNamespace

from waygate_workflows.utils import resolve_storage


def _normalize_source_type_slug(source_type: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", source_type.strip().lower())
    return slug.strip("-")


def _read_optional_guidance(document_path: str) -> str | None:
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
