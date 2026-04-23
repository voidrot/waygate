from __future__ import annotations

import re

from waygate_core.logging import get_logger
from waygate_core.plugin import StorageNamespace

from waygate_workflows.runtime.storage import resolve_storage

logger = get_logger(__name__)


def _normalize_source_type_slug(source_type: str) -> str:
    """Normalize a source type into the storage slug used for guidance docs."""
    slug = re.sub(r"[^a-z0-9]+", "-", source_type.strip().lower())
    return slug.strip("-")


def _read_optional_guidance(document_path: str) -> str | None:
    """Read optional agent guidance text from storage."""
    try:
        storage = resolve_storage()
    except Exception as exc:
        logger.warning(
            "Skipping optional guidance because storage resolution failed",
            document_path=document_path,
            detail=str(exc),
        )
        return None

    namespaced_path = storage.build_namespaced_path(
        StorageNamespace.Agents,
        document_path,
    )
    try:
        content = storage.read_document(namespaced_path).strip()
    except FileNotFoundError, KeyError:
        logger.debug(
            "Optional guidance document not found",
            document_path=document_path,
            namespaced_path=namespaced_path,
        )
        return None
    logger.debug(
        "Loaded optional guidance document",
        document_path=document_path,
        namespaced_path=namespaced_path,
        content_length=len(content),
    )
    return content or None


def load_agent_guidance_instructions(
    *,
    workflow_name: str,
    role_name: str,
    source_type: str | None = None,
) -> list[str]:
    """Load guidance snippets for a workflow role."""
    instructions: list[str] = []
    logger.debug(
        "Loading agent guidance instructions",
        workflow_name=workflow_name,
        role_name=role_name,
        source_type=source_type,
    )

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

    logger.debug(
        "Loaded agent guidance instructions",
        workflow_name=workflow_name,
        role_name=role_name,
        source_type=source_type,
        guidance_count=len(instructions),
    )
    return instructions
