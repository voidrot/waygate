"""Tests for LocalStorageProvider: canonical frontmatter write + metadata query."""

from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import pytest

from waygate_core.doc_helpers import generate_frontmatter
from waygate_core.schemas import (
    FrontMatterDocument,
    RawDocument,
    SourceMetadataBase,
    Visibility,
)
from waygate_plugin_local_storage.local_storage import LocalStorageProvider


@pytest.fixture()
def storage(tmp_path: Path) -> LocalStorageProvider:
    """Provide a LocalStorageProvider backed by a temp directory."""
    provider = LocalStorageProvider.__new__(LocalStorageProvider)
    provider.base_dir = tmp_path
    provider.raw_dir = tmp_path / "raw"
    provider.live_dir = tmp_path / "live"
    provider.staging_dir = tmp_path / "staging"
    provider.meta_dir = tmp_path / "meta"
    provider.templates_dir = provider.meta_dir / "templates"
    provider.agents_dir = provider.meta_dir / "agents"
    provider.raw_dir.mkdir()
    provider.live_dir.mkdir()
    provider.staging_dir.mkdir()
    provider.templates_dir.mkdir(parents=True)
    provider.agents_dir.mkdir(parents=True)
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

        assert "raw/web/" in filepath.as_posix()
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

    def test_filenames_are_unique_with_same_timestamp_and_source_type(
        self, storage: LocalStorageProvider
    ) -> None:
        doc1 = _make_doc(source_id="src-1")
        doc2 = _make_doc(source_id="src-2")

        uris = storage.write_raw_documents([doc1, doc2])

        assert len(uris) == 2
        assert uris[0] != uris[1]


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

    def test_invalid_timestamp_falls_back_without_crashing(
        self, storage: LocalStorageProvider
    ) -> None:
        filepath = storage.raw_dir / "bad-timestamp.md"
        post = frontmatter.Post(
            "Hello",
            doc_id="doc-bad-ts",
            source_type="web",
            source_id="s1",
            timestamp="not-a-real-timestamp",
            tags=["x"],
            visibility="internal",
        )
        filepath.write_text(frontmatter.dumps(post), encoding="utf-8")

        result = storage.get_raw_document_metadata("doc-bad-ts")

        assert result is not None
        assert isinstance(result.timestamp, datetime)


class TestManagedTopology:
    def test_write_live_document_to_category(
        self, storage: LocalStorageProvider
    ) -> None:
        uri = storage.write_live_document_to_category(
            "knowledge-base-12345678",
            "body",
            "thematic",
        )

        assert "/live/thematic/knowledge-base-12345678.md" in uri

    def test_get_live_document_metadata(self, storage: LocalStorageProvider) -> None:
        content = (
            generate_frontmatter(
                FrontMatterDocument(
                    doc_id="doc-123",
                    title="Knowledge Base",
                    status="live",
                )
            )
            + "\nBody"
        )
        uri = storage.write_live_document_to_category(
            "knowledge-base-12345678", content, "concepts"
        )

        metadata = storage.get_live_document_metadata(uri)

        assert metadata.doc_id == "doc-123"
        assert metadata.title == "Knowledge Base"

    def test_write_and_list_meta_documents(self, storage: LocalStorageProvider) -> None:
        uri = storage.write_meta_document("templates", "default", "# Template")

        assert uri == "meta/templates/default"
        assert storage.read_meta_document(uri) == "# Template"
        assert storage.list_meta_documents("templates") == [uri]
