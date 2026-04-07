from datetime import datetime, timezone

import pytest

from waygate_core.schemas import (
    FrontMatterDocument,
    RawDocument,
    SourceMetadataBase,
    SourceType,
    Visibility,
)


class FixtureSourceMetadata(SourceMetadataBase):
    kind: str = "test"
    repo_name: str | None = None


def test_raw_document_defaults_tags_to_empty_list() -> None:
    doc = RawDocument(
        source_type="github",
        source_id="pull/123",
        timestamp=datetime.now(timezone.utc),
        content="payload",
    )

    assert doc.tags == []


def test_raw_document_tags_default_is_not_shared_between_instances() -> None:
    first = RawDocument(
        source_type="slack",
        source_id="message-1",
        timestamp=datetime.now(timezone.utc),
        content="first",
    )
    second = RawDocument(
        source_type="slack",
        source_id="message-2",
        timestamp=datetime.now(timezone.utc),
        content="second",
    )

    first.tags.append("decision")

    assert second.tags == []


def test_frontmatter_document_defaults() -> None:
    metadata = FrontMatterDocument(
        title="Topic",
        last_compiled="2026-04-06T00:00:00+00:00",
        status="live",
    )

    assert metadata.doc_id
    assert metadata.source_type == SourceType.SYNTHESIS
    assert metadata.visibility == Visibility.INTERNAL
    assert metadata.tags == []
    assert metadata.lineage == []
    assert metadata.sources == []


def test_raw_document_supports_typed_source_metadata() -> None:
    doc = RawDocument(
        source_type="github",
        source_id="commit/abc123",
        timestamp=datetime.now(timezone.utc),
        content="payload",
        source_metadata=FixtureSourceMetadata(
            repo_name="voidrot/waygate",
        ),
    )

    assert doc.doc_id
    assert doc.source_metadata is not None
    assert isinstance(doc.source_metadata, FixtureSourceMetadata)
    assert doc.source_metadata.kind == "test"


def test_source_metadata_base_requires_kind_field() -> None:
    with pytest.raises(ValueError):
        SourceMetadataBase.model_validate({"repo_name": "voidrot/waygate"})


def test_source_metadata_base_allows_extra_fields() -> None:
    metadata = SourceMetadataBase.model_validate(
        {
            "kind": "web",
            "domain": "example.com",
            "author": "alice",
        }
    )

    assert metadata.kind == "web"
    assert metadata.model_extra is not None
    assert metadata.model_extra["domain"] == "example.com"
