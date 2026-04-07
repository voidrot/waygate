"""Tests for LocalStorageProvider: canonical frontmatter write + metadata query."""

from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import pytest

from waygate_core.schemas import RawDocument, SourceMetadataBase, Visibility
from waygate_plugin_local_storage.local_storage import LocalStorageProvider


@pytest.fixture()
def storage(tmp_path: Path) -> LocalStorageProvider:
    """Provide a LocalStorageProvider backed by a temp directory."""
    provider = LocalStorageProvider.__new__(LocalStorageProvider)
    provider.base_dir = tmp_path
    provider.raw_dir = tmp_path / "raw"
    provider.live_dir = tmp_path / "live"
    provider.raw_dir.mkdir()
    provider.live_dir.mkdir()
    return provider


def _make_doc(**overrides) -> RawDocument:
    defaults: dict = dict(
        source_type="web",
        source_id="test-source-1",
        timestamp=datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
        content="Hello world",
        tags=["a", "b"],
        source_url="https://example.com/page",
        source_hash="abc123",
        visibility=Visibility.INTERNAL,
    )
    defaults.update(overrides)
    return RawDocument.model_validate(defaults)


class TestWriteRawDocuments:
    def test_returns_file_uris(self, storage: LocalStorageProvider) -> None:
        doc = _make_doc()
        uris = storage.write_raw_documents([doc])
        assert len(uris) == 1
        assert uris[0].startswith("file://")

    def test_file_has_canonical_frontmatter(
        self, storage: LocalStorageProvider
    ) -> None:
        doc = _make_doc()
        uris = storage.write_raw_documents([doc])
        filepath = Path(uris[0].replace("file://", ""))

        post = frontmatter.load(str(filepath))
        assert post.metadata["doc_id"] == doc.doc_id
        assert post.metadata["source_type"] == "web"
        assert post.metadata["source_id"] == "test-source-1"
        assert post.metadata["source_url"] == "https://example.com/page"
        assert post.metadata["source_hash"] == "abc123"
        assert post.metadata["visibility"] == "internal"
        assert post.metadata["tags"] == ["a", "b"]
        assert post.content == "Hello world"

    def test_source_metadata_serialised(self, storage: LocalStorageProvider) -> None:
        class FixtureMeta(SourceMetadataBase):
            kind: str = "web"
            domain: str = "example.com"

        doc = _make_doc(source_metadata=FixtureMeta())
        uris = storage.write_raw_documents([doc])
        filepath = Path(uris[0].replace("file://", ""))

        post = frontmatter.load(str(filepath))
        sm = post.metadata.get("source_metadata")
        assert isinstance(sm, dict)
        assert sm["kind"] == "web"
        assert sm["domain"] == "example.com"

    def test_optional_fields_absent_when_none(
        self, storage: LocalStorageProvider
    ) -> None:
        doc = _make_doc(source_url=None, source_hash=None, source_metadata=None)
        uris = storage.write_raw_documents([doc])
        filepath = Path(uris[0].replace("file://", ""))

        post = frontmatter.load(str(filepath))
        assert "source_url" not in post.metadata
        assert "source_hash" not in post.metadata
        assert "source_metadata" not in post.metadata


class TestGetRawDocumentMetadata:
    def test_returns_matching_document(self, storage: LocalStorageProvider) -> None:
        doc = _make_doc()
        storage.write_raw_documents([doc])

        result = storage.get_raw_document_metadata(doc.doc_id)

        assert result is not None
        assert result.doc_id == doc.doc_id
        assert result.source_type == "web"
        assert result.source_id == "test-source-1"
        assert result.source_url == "https://example.com/page"
        assert result.source_hash == "abc123"
        assert result.visibility == Visibility.INTERNAL
        assert result.tags == ["a", "b"]
        assert result.content == "Hello world"

    def test_returns_none_for_unknown_doc_id(
        self, storage: LocalStorageProvider
    ) -> None:
        doc = _make_doc()
        storage.write_raw_documents([doc])

        assert storage.get_raw_document_metadata("does-not-exist") is None

    def test_source_metadata_round_trips(self, storage: LocalStorageProvider) -> None:
        class FixtureMeta(SourceMetadataBase):
            kind: str = "web"
            domain: str = "example.com"

        doc = _make_doc(source_metadata=FixtureMeta())
        storage.write_raw_documents([doc])

        result = storage.get_raw_document_metadata(doc.doc_id)
        assert result is not None
        assert result.source_metadata is not None
        # `kind` is a declared base field; plugin-specific extras land in model_extra
        assert result.source_metadata.kind == "web"
        extra = result.source_metadata.model_extra or {}
        assert extra.get("domain") == "example.com"

    def test_returns_none_when_raw_dir_empty(
        self, storage: LocalStorageProvider
    ) -> None:
        assert storage.get_raw_document_metadata("any-id") is None
