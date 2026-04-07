from datetime import UTC, datetime
from typing import Iterable, List

import frontmatter
from pydantic import ValidationError

from waygate_storage.storage_base import StorageProvider
from pathlib import Path
from waygate_core.plugin_base import RawDocument
from waygate_core.doc_helpers import generate_raw_document, slugify
from waygate_core.settings import get_runtime_settings
from waygate_core.schemas import FrontMatterDocument, SourceMetadataBase, Visibility


class LocalStorageProvider(StorageProvider):
    def __init__(self):
        settings = get_runtime_settings()
        base_dir = Path(settings.local_storage_path)
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.live_dir = self.base_dir / "live"
        self.staging_dir = self.base_dir / "staging"
        self.meta_dir = self.base_dir / "meta"
        self.templates_dir = self.meta_dir / "templates"
        self.agents_dir = self.meta_dir / "agents"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.live_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.agents_dir.mkdir(parents=True, exist_ok=True)

    @property
    def provider_name(self) -> str:
        return "local"

    def _get_real_path(self, uri: str) -> Path:
        if uri.startswith("file://"):
            return Path(uri.replace("file://", ""))

        normalized_uri = uri.strip("/")
        namespace_roots = {
            "raw": self.raw_dir,
            "live": self.live_dir,
            "meta": self.meta_dir,
        }

        for namespace, root_dir in namespace_roots.items():
            if normalized_uri == namespace or normalized_uri.startswith(
                f"{namespace}/"
            ):
                relative_parts = normalized_uri.split("/")[1:]
                candidate = (
                    root_dir.joinpath(*relative_parts) if relative_parts else root_dir
                )
                if relative_parts and candidate.suffix == "":
                    candidate = candidate.with_suffix(".md")

                resolved_root = root_dir.resolve(strict=False)
                resolved_candidate = candidate.resolve(strict=False)
                try:
                    resolved_candidate.relative_to(resolved_root)
                except ValueError as exc:
                    raise ValueError(f"Path escapes storage root in {uri}") from exc

                return resolved_candidate

        raise ValueError(f"Unsupported URI scheme in {uri}")

    def _iter_markdown_files(self, directory: Path) -> Iterable[Path]:
        return directory.rglob("*.md")

    def _raw_source_dir(self, source_type: str) -> Path:
        directory = self.raw_dir / slugify(source_type or "unknown")
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _live_category_dir(self, category: str) -> Path:
        directory = self.live_dir / slugify(category or "concepts")
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _meta_namespace_dir(self, namespace: str) -> Path:
        directory = self.meta_dir / slugify(namespace)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def write_raw_documents(self, documents: List[RawDocument]) -> List[str]:
        saved_uris = []
        for doc in documents:
            filename = f"{doc.timestamp.strftime('%Y%m%d%H%M%S')}_{doc.source_type}_{doc.doc_id}.md"
            filepath = self._raw_source_dir(doc.source_type) / filename
            filepath.write_text(generate_raw_document(doc), encoding="utf-8")
            saved_uris.append(f"file://{filepath.absolute()}")
        return saved_uris

    def read_raw_document(self, uri: str) -> str:
        filepath = self._get_real_path(uri)
        return filepath.read_text(encoding="utf-8")

    def delete_raw_document(self, uri: str) -> None:
        filepath = self._get_real_path(uri)
        filepath.unlink()

    def list_raw_documents(self, prefix: str = "") -> List[str]:
        uris = []
        for filepath in self._iter_markdown_files(self.raw_dir):
            if filepath.is_file():
                relative_path = filepath.relative_to(self.raw_dir).as_posix()
                if prefix and not relative_path.startswith(prefix):
                    continue
                uris.append(f"file://{filepath.absolute()}")
        return uris

    def get_raw_document_metadata(self, doc_id: str) -> RawDocument | None:
        for filepath in self._iter_markdown_files(self.raw_dir):
            post = frontmatter.load(str(filepath))
            if post.metadata.get("doc_id") != doc_id:
                continue

            m = post.metadata
            raw_ts = m.get("timestamp")
            if isinstance(raw_ts, datetime):
                timestamp = raw_ts
            else:
                timestamp = datetime.fromtimestamp(filepath.stat().st_mtime, tz=UTC)
                if raw_ts:
                    try:
                        parsed = datetime.fromisoformat(str(raw_ts))
                        timestamp = (
                            parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
                        )
                    except TypeError, ValueError:
                        pass

            raw_sm = m.get("source_metadata")
            source_metadata: SourceMetadataBase | None = None
            if isinstance(raw_sm, dict):
                try:
                    source_metadata = SourceMetadataBase.model_validate(raw_sm)
                except ValidationError:
                    # Old documents may not have a `kind` field; treat as opaque.
                    source_metadata = None

            return RawDocument.model_validate(
                {
                    "doc_id": m["doc_id"],
                    "source_type": m["source_type"],
                    "source_id": m["source_id"],
                    "timestamp": timestamp,
                    "content": post.content,
                    "tags": m.get("tags", []),
                    "source_url": m.get("source_url"),
                    "source_hash": m.get("source_hash"),
                    "visibility": m.get("visibility", Visibility.INTERNAL),
                    "source_metadata": source_metadata,
                }
            )

        return None

    def write_live_document(self, document_id: str, content: str) -> str:
        return self.write_live_document_to_category(document_id, content, "concepts")

    def write_live_document_to_category(
        self, document_id: str, content: str, category: str
    ) -> str:
        filename = f"{document_id}.md"
        filepath = self._live_category_dir(category) / filename
        filepath.write_text(content, encoding="utf-8")
        return f"file://{filepath.absolute()}"

    def read_live_document(self, uri: str) -> str:
        filepath = self._get_real_path(uri)
        return filepath.read_text(encoding="utf-8")

    def write_staging_document(self, document_id: str, content: str) -> str:
        filename = f"{document_id}.md"
        filepath = self.staging_dir / filename
        filepath.write_text(content, encoding="utf-8")
        return f"file://{filepath.absolute()}"

    def list_live_documents(self, prefix: str = "") -> List[str]:
        uris = []
        for filepath in self._iter_markdown_files(self.live_dir):
            if filepath.is_file():
                relative_path = filepath.relative_to(self.live_dir).as_posix()
                if prefix and not relative_path.startswith(prefix):
                    continue
                uris.append(f"file://{filepath.absolute()}")
        return uris

    def write_meta_document(
        self, namespace: str, document_id: str, content: str
    ) -> str:
        filename = f"{document_id}.md"
        normalized_namespace = slugify(namespace)
        filepath = self._meta_namespace_dir(normalized_namespace) / filename
        filepath.write_text(content, encoding="utf-8")
        return f"meta/{normalized_namespace}/{document_id}"

    def read_meta_document(self, uri: str) -> str:
        filepath = self._get_real_path(uri)
        return filepath.read_text(encoding="utf-8")

    def list_meta_documents(self, namespace: str, prefix: str = "") -> List[str]:
        normalized_namespace = slugify(namespace)
        base_dir = self._meta_namespace_dir(normalized_namespace)
        uris = []
        for filepath in self._iter_markdown_files(base_dir):
            if filepath.is_file() and filepath.name.startswith(prefix):
                uris.append(f"meta/{normalized_namespace}/{filepath.stem}")
        return uris

    def get_live_document_metadata(self, uri: str) -> FrontMatterDocument:
        filepath = self._get_real_path(uri)
        post = frontmatter.load(str(filepath))
        metadata = dict(post.metadata)
        if metadata.get("source_metadata") == {}:
            metadata["source_metadata"] = None
        return FrontMatterDocument.model_validate(metadata)
