"""Jinja-backed document rendering helpers for WayGate document artifacts."""

import hashlib
import json
import os
import re
from functools import lru_cache
from importlib.util import find_spec
from urllib.parse import unquote, urlparse

import content_types
import frontmatter
from pydantic import BaseModel
from jinja2 import ChoiceLoader, Environment, PackageLoader, Template, TemplateNotFound

from waygate_core.config.schema import CoreSettings
from waygate_core.schema import (
    CompiledDocument,
    CompiledDocumentFrontmatter,
    PublishedDocument,
    PublishedDocumentFrontmatter,
    RawDocument,
    RawDocumentFrontmatter,
)

_HTML_PREFIXES = (
    "<!doctype html",
    "<html",
    "<head",
    "<body",
)
_DEFAULT_BINARY_CONTENT_TYPE = "application/octet-stream"
_XML_PATTERN = re.compile(r"^<(\?xml\b|[A-Za-z_][\w:.-]*\b)")
_MARKDOWN_PATTERNS = (
    re.compile(r"^#{1,6}\s", re.MULTILINE),
    re.compile(r"^```", re.MULTILINE),
    re.compile(r"^[-*+]\s", re.MULTILINE),
    re.compile(r"^>\s", re.MULTILINE),
    re.compile(r"^\d+\.\s", re.MULTILINE),
)


def normalize_document_body(content: str) -> str:
    """Normalize raw document body content before hashing or parsing."""

    return content.replace("\r\n", "\n").replace("\r", "\n").strip()


def compute_content_hash(content: str) -> str:
    """Build a stable body-only content hash for raw and compiled artifacts."""

    normalized = normalize_document_body(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _extract_filename_candidate(source_name: str | None) -> str | None:
    """Extract a filename-like token from a URI, path, or document name."""

    if source_name is None:
        return None

    text = source_name.strip()
    if not text:
        return None

    parsed = urlparse(text)
    path = parsed.path or text
    if parsed.scheme == "file" and not parsed.path and parsed.netloc:
        path = parsed.netloc

    filename = unquote(path).rstrip("/").rsplit("/", 1)[-1].strip()
    if not filename or "." not in filename:
        return None
    return filename


@lru_cache(maxsize=256)
def _infer_content_type_from_filename(filename: str) -> str | None:
    """Resolve a MIME type from a filename extension when available."""

    inferred = content_types.get_content_type(filename)
    if inferred == _DEFAULT_BINARY_CONTENT_TYPE:
        return None
    return inferred


def normalize_content_type(content_type: str | None) -> str | None:
    """Canonicalize an explicit content type onto the MIME-style contract."""

    if content_type is None:
        return None

    normalized = content_type.strip().lower()
    if not normalized:
        return None
    if "/" in normalized:
        return normalized

    inferred = _infer_content_type_from_filename(f"file.{normalized.lstrip('.')}")
    if inferred is not None:
        return inferred

    return normalized


def infer_content_type(
    content: str,
    *,
    source_uri: str | None = None,
    source_id: str | None = None,
) -> str:
    """Infer a content type from source metadata and body text.

    The helper prefers source filename extensions when a document URI or source
    identifier is available. When no useful extension can be derived, it falls
    back to lightweight body heuristics and returns a standard MIME string.
    """

    for source_name in (source_uri, source_id):
        filename = _extract_filename_candidate(source_name)
        if filename is None:
            continue
        inferred = _infer_content_type_from_filename(filename)
        if inferred is not None:
            return inferred

    normalized = normalize_document_body(content)
    if not normalized:
        return "text/plain"

    if normalized[0] in {"{", "["}:
        try:
            json.loads(normalized)
        except json.JSONDecodeError:
            pass
        else:
            return "application/json"

    lowered = normalized.lower()
    if lowered.startswith(_HTML_PREFIXES):
        return "text/html"

    if _XML_PATTERN.match(normalized):
        return "application/xml"

    if any(pattern.search(normalized) for pattern in _MARKDOWN_PATTERNS):
        return "text/markdown"

    if "\n[" in normalized and "](" in normalized:
        return "text/markdown"

    return "text/plain"


@lru_cache(maxsize=1)
def _get_template_settings() -> tuple[tuple[str, ...], str, str, str]:
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
    compiled_doc_template = os.getenv(
        "WAYGATE_CORE__COMPILED_DOC_TEMPLATE",
        os.getenv(
            "WAYGATE_CORE__COMPILED_DOCUMENT_TEMPLATE",
            defaults.compiled_doc_template,
        ),
    )
    published_doc_template = os.getenv(
        "WAYGATE_CORE__PUBLISHED_DOC_TEMPLATE",
        os.getenv(
            "WAYGATE_CORE__PUBLISHED_DOCUMENT_TEMPLATE",
            defaults.published_doc_template,
        ),
    )

    return (
        packages,
        raw_doc_template,
        compiled_doc_template,
        published_doc_template,
    )


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
        content_type=normalize_content_type(raw_doc.content_type)
        or infer_content_type(
            raw_doc.content,
            source_uri=raw_doc.source_uri,
            source_id=raw_doc.source_id,
        ),
        source_id=raw_doc.source_id,
        source_hash=raw_doc.source_hash,
        content_hash=raw_doc.content_hash or compute_content_hash(raw_doc.content),
        source_uri=raw_doc.source_uri,
        timestamp=raw_doc.timestamp,
        topics=raw_doc.topics or [],
        tags=raw_doc.tags or [],
    )


def _normalize_frontmatter_list(values: list[str | None]) -> list[str]:
    """Drop empty string-like values while preserving input order."""

    normalized: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        normalized.append(text)
    return normalized


def build_compiled_document_frontmatter(
    compiled_doc: CompiledDocument,
) -> CompiledDocumentFrontmatter:
    """Build frontmatter from a compiled document artifact."""

    return CompiledDocumentFrontmatter(
        doc_id=compiled_doc.doc_id,
        source_set_key=compiled_doc.source_set_key,
        source_documents=[reference.uri for reference in compiled_doc.source_documents],
        source_content_hashes=_normalize_frontmatter_list(
            [reference.content_hash for reference in compiled_doc.source_documents]
        ),
        source_hashes=_normalize_frontmatter_list(
            [reference.source_hash for reference in compiled_doc.source_documents]
        ),
        source_uris=_normalize_frontmatter_list(
            [reference.source_uri for reference in compiled_doc.source_documents]
        ),
        compiled_at=compiled_doc.compiled_at,
        review_feedback=compiled_doc.review_feedback,
        topics=compiled_doc.topics,
        tags=compiled_doc.tags,
        people=compiled_doc.people,
        organizations=compiled_doc.organizations,
        projects=compiled_doc.projects,
    )


def build_published_document_frontmatter(
    published_doc: PublishedDocument,
) -> PublishedDocumentFrontmatter:
    """Build frontmatter from a published document artifact."""

    return PublishedDocumentFrontmatter(
        doc_id=published_doc.doc_id,
        compiled_document_ids=published_doc.compiled_document_ids,
        compiled_document_uris=published_doc.compiled_document_uris,
        source_set_keys=published_doc.source_set_keys,
        published_at=published_doc.published_at,
        topics=published_doc.topics,
        tags=published_doc.tags,
        people=published_doc.people,
        organizations=published_doc.organizations,
        projects=published_doc.projects,
    )


def _serialize_frontmatter(doc_frontmatter: BaseModel) -> str:
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

    packages, raw_doc_template_name, _, _ = _get_template_settings()
    raw_doc_template = _get_template(packages, raw_doc_template_name)

    resolved_frontmatter = doc_frontmatter or build_raw_document_frontmatter(raw_doc)
    serialized_frontmatter = _serialize_frontmatter(resolved_frontmatter)

    return raw_doc_template.render(
        frontmatter=serialized_frontmatter, raw_content=raw_doc.content
    )


def render_compiled_document(
    compiled_doc: CompiledDocument,
    doc_frontmatter: CompiledDocumentFrontmatter | None = None,
) -> str:
    """Render a compiled document using the configured template."""

    packages, _, compiled_doc_template_name, _ = _get_template_settings()
    compiled_doc_template = _get_template(packages, compiled_doc_template_name)
    resolved_frontmatter = doc_frontmatter or build_compiled_document_frontmatter(
        compiled_doc
    )
    serialized_frontmatter = _serialize_frontmatter(resolved_frontmatter)
    return compiled_doc_template.render(
        frontmatter=serialized_frontmatter,
        content=compiled_doc.content,
    )


def render_published_document(
    published_doc: PublishedDocument,
    doc_frontmatter: PublishedDocumentFrontmatter | None = None,
) -> str:
    """Render a published document using the configured template."""

    packages, _, _, published_doc_template_name = _get_template_settings()
    published_doc_template = _get_template(packages, published_doc_template_name)
    resolved_frontmatter = doc_frontmatter or build_published_document_frontmatter(
        published_doc
    )
    serialized_frontmatter = _serialize_frontmatter(resolved_frontmatter)
    return published_doc_template.render(
        frontmatter=serialized_frontmatter,
        content=published_doc.content,
    )
