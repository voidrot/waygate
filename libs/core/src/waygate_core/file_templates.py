from string import Template

from waygate_core.schemas import DocumentType


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


def render_markdown_template(title: str, document_type: str | None = None) -> str:
    template = Template(get_markdown_template(document_type))
    return template.safe_substitute(title=title)
