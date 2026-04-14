from datetime import datetime, timezone

from waygate_core.files.template import (
    build_raw_document_frontmatter,
    render_draft_document,
    render_raw_document,
)
from waygate_core.schema import RawDocument, RawDocumentFrontmatter


def test_build_raw_document_frontmatter_from_raw_document() -> None:
    raw_doc = RawDocument(
        source_type="manual",
        source_id="doc-123",
        source_hash="abc123",
        source_uri="file://raw/doc-123.md",
        timestamp=datetime(2026, 4, 11, 12, 0, tzinfo=timezone.utc),
        topics=["waygate", "core"],
        tags=["example"],
        content="hello world",
    )

    frontmatter = build_raw_document_frontmatter(raw_doc)

    assert frontmatter.source_type == raw_doc.source_type
    assert frontmatter.source_id == raw_doc.source_id
    assert frontmatter.source_hash == raw_doc.source_hash
    assert frontmatter.source_uri == raw_doc.source_uri
    assert frontmatter.timestamp == raw_doc.timestamp
    assert frontmatter.topics == raw_doc.topics
    assert frontmatter.tags == raw_doc.tags


def test_render_raw_document_builds_frontmatter_when_not_provided() -> None:
    raw_doc = RawDocument(
        source_type="manual",
        source_id="doc-456",
        timestamp=datetime(2026, 4, 11, 13, 30, tzinfo=timezone.utc),
        topics=["waygate"],
        tags=["render"],
        content="raw body content",
    )

    rendered = render_raw_document(raw_doc)

    assert rendered.startswith("---\n")
    assert "source_type: manual" in rendered
    assert "source_id: doc-456" in rendered
    assert "topics:" in rendered
    assert "- waygate" in rendered
    assert "<raw_document>" in rendered
    assert "raw body content" in rendered


def test_render_raw_document_uses_provided_frontmatter_override() -> None:
    raw_doc = RawDocument(
        source_type="manual",
        source_id="doc-789",
        timestamp=datetime(2026, 4, 11, 14, 0, tzinfo=timezone.utc),
        content="payload",
    )
    override = RawDocumentFrontmatter(
        source_type="override",
        source_id="fm-1",
        topics=["custom-topic"],
        tags=["custom-tag"],
    )

    rendered = render_raw_document(raw_doc, override)

    assert "source_type: override" in rendered
    assert "source_id: fm-1" in rendered
    assert "- custom-topic" in rendered
    assert "- custom-tag" in rendered
    assert "payload" in rendered


def test_render_draft_document_serializes_document_context() -> None:
    rendered = render_draft_document(
        context={"source_type": "manual", "topics": ["waygate"]},
        content="draft source body",
        doc_uri="raw/doc-1.md",
    )

    assert "<source_document uri='raw/doc-1.md'>" in rendered
    assert '"source_type": "manual"' in rendered
    assert '"topics": [' in rendered
    assert "draft source body" in rendered
