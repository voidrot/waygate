from datetime import datetime, timezone

from waygate_core.doc_helpers import (
    build_live_document_name,
    extract_markdown_title,
    generate_frontmatter,
    generate_raw_document,
    infer_initial_topic,
    slugify,
)
from waygate_core.schemas import FrontMatterDocument, RawDocument, SourceMetadataBase


class FixtureWebSourceMetadata(SourceMetadataBase):
    kind: str = "web"
    author: str | None = None
    domain: str | None = None
    keywords: list[str] = []


def test_slugify_replaces_whitespace_and_symbols() -> None:
    assert slugify("Hello, WayGate! Docs") == "hello-waygate-docs"


def test_generate_frontmatter_with_empty_tags_and_sources() -> None:
    metadata = FrontMatterDocument(
        doc_id="doc-123",
        title="Knowledge Base",
        last_compiled="2026-04-06T12:00:00+00:00",
        status="live",
    )

    frontmatter = generate_frontmatter(metadata)

    assert frontmatter == (
        "---\n"
        "doc_id: doc-123\n"
        "title: Knowledge Base\n"
        "document_type: concepts\n"
        "source_type: synthesis\n"
        "status: live\n"
        "visibility: internal\n"
        "tags: []\n"
        "last_compiled: 2026-04-06T12:00:00+00:00\n"
        "lineage: []\n"
        "sources: []\n"
        "source_metadata: {}\n"
        "---\n"
    )


def test_generate_frontmatter_with_tags_and_sources() -> None:
    source_metadata = FixtureWebSourceMetadata.model_validate(
        {
            "author": "Buck",
            "domain": "example.com",
            "keywords": ["gar", "metadata"],
        }
    )

    metadata = FrontMatterDocument(
        doc_id="doc-456",
        title="Knowledge Base",
        last_compiled="2026-04-06T12:00:00+00:00",
        source_url="https://example.com/raw",
        source_hash="abc123",
        status="draft",
        tags=["architecture", "platform"],
        lineage=["raw-1", "raw-2"],
        sources=["file:///tmp/raw1.md", "file:///tmp/raw2.md"],
        source_metadata=source_metadata,
    )

    frontmatter = generate_frontmatter(metadata)

    assert "doc_id: doc-456\n" in frontmatter
    assert "document_type: concepts\n" in frontmatter
    assert "source_type: synthesis\n" in frontmatter
    assert "source_url: https://example.com/raw\n" in frontmatter
    assert "source_hash: abc123\n" in frontmatter
    assert "visibility: internal\n" in frontmatter
    assert "last_compiled: 2026-04-06T12:00:00+00:00\n" in frontmatter
    assert "lineage:\n  - raw-1\n  - raw-2\n" in frontmatter
    assert "tags:\n  - architecture\n  - platform\n" in frontmatter
    assert "sources:\n  - file:///tmp/raw1.md\n  - file:///tmp/raw2.md\n" in frontmatter
    assert (
        "source_metadata:\n  kind: web\n  author: Buck\n  domain: example.com\n"
        in frontmatter
    )
    assert "  keywords:\n    - gar\n    - metadata\n" in frontmatter


def test_extract_markdown_title_prefers_first_heading() -> None:
    draft = "# Final Title\n\nBody"

    assert extract_markdown_title(draft, "Fallback") == "Final Title"


def test_infer_initial_topic_uses_source_context() -> None:
    documents = [
        RawDocument(
            source_type="github",
            source_id="issue/1",
            timestamp=datetime(2026, 4, 6, tzinfo=timezone.utc),
            content="hello",
        )
    ]

    assert infer_initial_topic(documents) == "Github issue 1"


def test_generate_raw_document_emits_canonical_frontmatter() -> None:
    document = RawDocument(
        source_type="web",
        source_id="page-1",
        timestamp=datetime(2026, 4, 6, 12, 0, tzinfo=timezone.utc),
        content="Hello world",
        tags=["gar"],
    )

    raw_output = generate_raw_document(document)

    assert "doc_id:" in raw_output
    assert "source_type: web\n" in raw_output
    assert "source_id: page-1\n" in raw_output
    assert "tags:\n  - gar\n" in raw_output
    assert raw_output.endswith("\nHello world")


def test_build_live_document_name_adds_stable_suffix() -> None:
    assert (
        build_live_document_name("WayGate Contract", "12345678-abcd")
        == "waygate-contract-12345678.md"
    )
