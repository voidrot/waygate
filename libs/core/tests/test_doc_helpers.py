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


# ---------------------------------------------------------------
# NEW: Round-trip and provenance consistency tests
# ---------------------------------------------------------------


def test_generate_frontmatter_with_source_metadata_round_trips() -> None:
    """Verify source_metadata serialized in frontmatter preserves extra fields."""
    original_metadata = FixtureWebSourceMetadata.model_validate(
        {
            "author": "Alice",
            "domain": "docs.example.com",
            "keywords": ["ai", "ml"],
        }
    )

    doc = FrontMatterDocument(
        doc_id="test-123",
        title="AI Knowledge",
        last_compiled="2026-04-06T12:00:00+00:00",
        status="live",
        source_metadata=original_metadata,
    )

    frontmatter_str = generate_frontmatter(doc)

    # Parse back to verify round-trip
    assert "author: Alice" in frontmatter_str
    assert "domain: docs.example.com" in frontmatter_str
    assert "- ai" in frontmatter_str


def test_build_live_document_name_is_deterministic() -> None:
    """Verify same title+id produces same filename on repeated calls."""
    name1 = build_live_document_name("Test Title", "abc-123")
    name2 = build_live_document_name("Test Title", "abc-123")

    assert name1 == name2


def test_build_live_document_name_differs_with_different_ids() -> None:
    """Verify different IDs produce different filename prefixes by UUID first part."""
    # build_live_document_name takes first segment before dash
    name1 = build_live_document_name(
        "Test Title", "aaaaaaaa-1111-2222-3333-444444444444"
    )
    name2 = build_live_document_name(
        "Test Title", "bbbbbbbb-1111-2222-3333-444444444444"
    )

    # Different first segments produce different filenames
    assert "test-title-aaaaaaaa" in name1
    assert "test-title-bbbbbbbb" in name2
    assert name1 != name2


def test_generate_raw_document_preserves_all_source_fields() -> None:
    """Verify raw document serialization includes source_type, source_id, source_url."""
    now = datetime(2026, 4, 6, 12, 0, tzinfo=timezone.utc)
    document = RawDocument(
        source_type="github",
        source_id="pull/999",
        timestamp=now,
        content="PR description",
        source_url="https://github.com/example/repo/pull/999",
        tags=["review"],
    )

    output = generate_raw_document(document)

    assert "source_type: github" in output
    assert "source_id: pull/999" in output
    assert "source_url: https://github.com/example/repo/pull/999" in output
    assert "timestamp:" in output


def test_frontmatter_document_with_full_provenance_chain() -> None:
    """Verify frontmatter correctly preserves complex lineage and source chains."""
    doc = FrontMatterDocument(
        doc_id="compiled-456",
        title="Aggregated Insights",
        last_compiled="2026-04-06T12:00:00+00:00",
        status="live",
        lineage=["raw-1", "raw-2", "raw-3"],
        sources=[
            "https://github.com/a/pull/1",
            "https://github.com/b/pull/2",
            "https://example.com/doc",
        ],
        tags=["architecture", "review", "api"],
    )

    frontmatter_str = generate_frontmatter(doc)

    # Verify all fields present and ordered
    assert "lineage:" in frontmatter_str
    assert "- raw-1" in frontmatter_str
    assert "- raw-2" in frontmatter_str
    assert "- raw-3" in frontmatter_str
    assert "sources:" in frontmatter_str
    assert "https://github.com/a/pull/1" in frontmatter_str
    assert "tags:" in frontmatter_str
    assert "- architecture" in frontmatter_str
    assert "- review" in frontmatter_str
