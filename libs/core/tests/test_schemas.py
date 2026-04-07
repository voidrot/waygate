from datetime import datetime, timezone

import pytest

from waygate_core.schemas import (
    AuditEvent,
    AuditEventType,
    ContextErrorReport,
    DocumentType,
    FrontMatterDocument,
    MaintenanceFinding,
    MaintenanceFindingType,
    RawDocument,
    RecompilationSignal,
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
    assert metadata.document_type == DocumentType.CONCEPTS
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


# ---------------------------------------------------------------
# NEW: Comprehensive validation edge cases
# ---------------------------------------------------------------


def test_raw_document_doc_id_is_generated_for_same_inputs() -> None:
    """Verify each instance gets a generated, non-empty doc_id for identical inputs."""
    now = datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)
    doc1 = RawDocument(
        source_type="github",
        source_id="pr/123",
        timestamp=now,
        content="content",
    )
    doc2 = RawDocument(
        source_type="github",
        source_id="pr/123",
        timestamp=now,
        content="content",
    )

    # Both should have doc_id, but they will be different (UUID4)
    assert doc1.doc_id
    assert doc2.doc_id
    assert len(doc1.doc_id) > 0
    assert len(doc2.doc_id) > 0


def test_raw_document_doc_id_differs_for_different_source_ids() -> None:
    """Verify doc_id changes when source_id differs."""
    now = datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)
    doc1 = RawDocument(
        source_type="github",
        source_id="pr/123",
        timestamp=now,
        content="content",
    )
    doc2 = RawDocument(
        source_type="github",
        source_id="pr/456",
        timestamp=now,
        content="content",
    )

    assert doc1.doc_id != doc2.doc_id


def test_frontmatter_document_with_empty_lineage() -> None:
    """Verify frontmatter handles empty lineage without crashing."""
    doc = FrontMatterDocument(
        title="Title",
        last_compiled="2026-04-06T00:00:00+00:00",
        status="live",
        lineage=[],
    )

    assert doc.lineage == []


def test_frontmatter_document_with_lineage_preserves_order() -> None:
    """Verify lineage list order is preserved."""
    doc = FrontMatterDocument(
        title="Title",
        last_compiled="2026-04-06T00:00:00+00:00",
        status="live",
        lineage=["id1", "id2", "id3"],
    )

    assert doc.lineage == ["id1", "id2", "id3"]


def test_frontmatter_document_with_sources_preserves_urls() -> None:
    """Verify sources list is preserved correctly."""
    doc = FrontMatterDocument(
        title="Title",
        last_compiled="2026-04-06T00:00:00+00:00",
        status="live",
        sources=["https://a.com", "https://b.com"],
    )

    assert doc.sources == ["https://a.com", "https://b.com"]


def test_raw_document_with_multiple_tags_preserved() -> None:
    """Verify tags array is correctly stored and retrieved."""
    doc = RawDocument(
        source_type="slack",
        source_id="msg/1",
        timestamp=datetime.now(timezone.utc),
        content="content",
        tags=["architecture", "decision", "framework"],
    )

    assert doc.tags == ["architecture", "decision", "framework"]


def test_document_type_enum_values_are_valid() -> None:
    """Verify all DocumentType enum members can be used."""
    for doc_type in DocumentType:
        doc = FrontMatterDocument(
            title="Test",
            last_compiled="2026-04-06T00:00:00+00:00",
            status="live",
            document_type=doc_type,
        )
        assert doc.document_type == doc_type


def test_visibility_enum_values_are_valid() -> None:
    """Verify all Visibility enum members can be used."""
    for vis in Visibility:
        doc = FrontMatterDocument(
            title="Test",
            last_compiled="2026-04-06T00:00:00+00:00",
            status="live",
            visibility=vis,
        )
        assert doc.visibility == vis


def test_audit_event_defaults_and_payload() -> None:
    event = AuditEvent(
        event_type=AuditEventType.MAINTENANCE_RECOMPILATION_ENQUEUED,
        occurred_at="2026-04-06T12:00:00+00:00",
        trace_id="trace-123",
        payload={"queue_name": "draft_tasks"},
    )

    assert event.event_id
    assert event.event_type == AuditEventType.MAINTENANCE_RECOMPILATION_ENQUEUED
    assert event.trace_id == "trace-123"
    assert event.document_ids == []
    assert event.uris == []
    assert event.payload["queue_name"] == "draft_tasks"


def test_maintenance_models_round_trip_payload() -> None:
    signal = RecompilationSignal(
        created_at="2026-04-06T12:00:00+00:00",
        live_document_uri="file:///tmp/live/doc-1.md",
        live_document_id="doc-1",
        reason="hash_mismatch",
        lineage=["raw-1"],
        payload={"expected_source_hash": "abc"},
    )
    report = ContextErrorReport(
        occurred_at="2026-04-06T12:00:00+00:00",
        message="Missing context",
        query="incident runbook",
        requested_visibilities=[Visibility.PUBLIC],
    )
    finding = MaintenanceFinding(
        finding_type=MaintenanceFindingType.STALE_COMPILATION,
        occurred_at="2026-04-06T12:00:00+00:00",
        live_document_id="doc-1",
        payload={"signal": signal.model_dump(mode="json")},
    )

    assert signal.reason == "hash_mismatch"
    assert report.requested_visibilities == [Visibility.PUBLIC]
    assert finding.finding_type == MaintenanceFindingType.STALE_COMPILATION
    assert finding.payload["signal"]["live_document_id"] == "doc-1"
