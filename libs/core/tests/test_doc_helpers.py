from typing import Literal

from waygate_core.doc_helpers import generate_frontmatter, slugify
from waygate_core.schemas import FrontMatterDocument, SourceMetadataBase


class FixtureWebSourceMetadata(SourceMetadataBase):
    kind: Literal["web"] = "web"
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
