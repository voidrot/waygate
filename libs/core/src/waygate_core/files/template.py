"""Jinja-backed document rendering helpers for raw and draft artifacts."""

import json
import os
from functools import lru_cache
from importlib.util import find_spec

import frontmatter
from jinja2 import ChoiceLoader, Environment, PackageLoader, Template, TemplateNotFound

from waygate_core.config.schema import CoreSettings
from waygate_core.schema import RawDocument, RawDocumentFrontmatter


@lru_cache(maxsize=1)
def _get_template_settings() -> tuple[tuple[str, ...], str, str]:
    """Resolve template package and template names from environment settings."""

    defaults = CoreSettings()

    raw_packages = os.getenv("WAYGATE_CORE__TEMPLATE_PACKAGES")
    if raw_packages:
        packages = tuple(
            item.strip() for item in raw_packages.split(",") if item.strip()
        )
    else:
        packages = tuple(defaults.template_packages)

    if not packages:
        packages = ("waygate_core",)

    raw_doc_template = os.getenv(
        "WAYGATE_CORE__RAW_DOC_TEMPLATE",
        os.getenv("WAYGATE_CORE__RAW_DOCUMENT_TEMPLATE", defaults.raw_doc_template),
    )
    draft_doc_template = os.getenv(
        "WAYGATE_CORE__DRAFT_DOC_TEMPLATE",
        os.getenv(
            "WAYGATE_CORE__DRAFT_DOCUMENT_TEMPLATE",
            defaults.draft_doc_template,
        ),
    )

    return (packages, raw_doc_template, draft_doc_template)


@lru_cache(maxsize=16)
def _build_template_env(packages: tuple[str, ...]) -> Environment:
    """Build a Jinja environment from the configured template packages."""

    loaders = []
    for package_name in packages:
        if not package_name:
            continue
        if find_spec(package_name) is None:
            continue
        loaders.append(PackageLoader(package_name, "templates"))

    if not loaders:
        joined = ", ".join(packages)
        raise RuntimeError(
            f"No templates loader could be initialized from configured packages: {joined}"
        )

    return Environment(loader=ChoiceLoader(loaders))


@lru_cache(maxsize=64)
def _get_template(packages: tuple[str, ...], template_name: str) -> Template:
    """Load and cache a named template from the configured packages."""

    env = _build_template_env(packages)
    try:
        return env.get_template(template_name)
    except TemplateNotFound as exc:
        joined = ", ".join(packages)
        raise RuntimeError(
            f"Template '{template_name}' was not found in configured template packages: {joined}"
        ) from exc


def build_raw_document_frontmatter(raw_doc: RawDocument) -> RawDocumentFrontmatter:
    """Build frontmatter from a raw document.

    Args:
        raw_doc: The raw document to convert.

    Returns:
        The serialized frontmatter model.
    """
    return RawDocumentFrontmatter(
        source_type=raw_doc.source_type,
        source_id=raw_doc.source_id,
        source_hash=raw_doc.source_hash,
        source_uri=raw_doc.source_uri,
        timestamp=raw_doc.timestamp,
        topics=raw_doc.topics or [],
        tags=raw_doc.tags or [],
    )


def _serialize_frontmatter(doc_frontmatter: RawDocumentFrontmatter) -> str:
    """Serialize frontmatter content without surrounding fences.

    Args:
        doc_frontmatter: The frontmatter model to serialize.

    Returns:
        The YAML frontmatter content without surrounding ``---`` fences.
    """
    post = frontmatter.Post("", **doc_frontmatter.model_dump(exclude_none=True))
    dumped = frontmatter.dumps(post)

    if dumped.startswith("---"):
        lines = dumped.splitlines()
        if lines and lines[0] == "---":
            for index in range(1, len(lines)):
                if lines[index] == "---":
                    return "\n".join(lines[1:index])

    return ""


def render_raw_document(
    raw_doc: RawDocument, doc_frontmatter: RawDocumentFrontmatter | None = None
) -> str:
    """Render a raw document using the configured template.

    Args:
        raw_doc: The raw document to render.
        doc_frontmatter: Optional prebuilt frontmatter model.

    Returns:
        The rendered raw document content.
    """

    packages, raw_doc_template_name, _ = _get_template_settings()
    raw_doc_template = _get_template(packages, raw_doc_template_name)

    resolved_frontmatter = doc_frontmatter or build_raw_document_frontmatter(raw_doc)
    serialized_frontmatter = _serialize_frontmatter(resolved_frontmatter)

    return raw_doc_template.render(
        frontmatter=serialized_frontmatter, raw_content=raw_doc.content
    )


def render_draft_document(context: dict, content: str, doc_uri: str) -> str:
    """Render a draft document using the configured template.

    Args:
        context: Structured context to embed in the rendered output.
        content: The draft markdown body.
        doc_uri: The document URI used by the template.

    Returns:
        The rendered draft document content.
    """

    packages, _, draft_doc_template_name = _get_template_settings()
    template = _get_template(packages, draft_doc_template_name)
    return template.render(
        document_context=json.dumps(context, indent=2, sort_keys=True, default=str),
        content=content,
        doc_uri=doc_uri,
    )
