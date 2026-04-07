import logging
from string import Template
from typing import TYPE_CHECKING, Any

from waygate_core.schemas import DocumentType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATES: dict[str, str] = {
    DocumentType.CONCEPTS.value: """# $title

## Summary

## Key Details

## References
""",
    DocumentType.ENTITIES.value: """# $title

## Overview

## Responsibilities

## Related Context
""",
    DocumentType.THEMATIC.value: """# $title

## Overview

## Major Themes

## Open Questions
""",
}


def get_markdown_template(document_type: str | None = None) -> str:
    template_key = document_type or DocumentType.CONCEPTS.value
    return DEFAULT_TEMPLATES.get(
        template_key, DEFAULT_TEMPLATES[DocumentType.CONCEPTS.value]
    )


def _load_template_from_storage(
    storage_provider: Any | None, document_type: str | None = None
) -> str | None:
    """Try to load a template from managed storage under meta/templates/.

    Returns None if not found or if storage provider is unavailable.
    """
    if storage_provider is None:
        return None

    template_key = document_type or DocumentType.CONCEPTS.value
    template_uri = f"meta/templates/{template_key}"

    try:
        content = storage_provider.read_meta_document(template_uri)
        logger.debug(f"Loaded template from storage: {template_uri}")
        return content
    except Exception as e:
        logger.debug(f"Template not found in storage ({template_uri}): {e}")
        return None


def render_markdown_template(
    title: str,
    document_type: str | None = None,
    storage_provider: Any | None = None,
) -> str:
    """Render a markdown template by substituting title.

    Attempts to load from storage if provider is available, falls back to
    packaged DEFAULT_TEMPLATES.

    Args:
        title: The title to substitute into the template
        document_type: The document type (e.g., 'concepts', 'entities')
        storage_provider: Optional storage provider for loading custom templates

    Returns:
        Rendered template with title substituted
    """
    # Try storage-backed template first if provider is available
    template_str = None
    if storage_provider is not None:
        template_str = _load_template_from_storage(storage_provider, document_type)

    # Fall back to packaged defaults
    if template_str is None:
        template_str = get_markdown_template(document_type)

    template = Template(template_str)
    return template.safe_substitute(title=title)
