from datetime import datetime
from typing import List

import frontmatter
from pydantic import ValidationError

from waygate_storage.storage_base import StorageProvider
from pathlib import Path
import os
from waygate_core.plugin_base import RawDocument
from waygate_core.schemas import SourceMetadataBase, Visibility


class LocalStorageProvider(StorageProvider):
    def __init__(self):
        base_dir = Path(os.getenv("LOCAL_STORAGE_PATH", "wiki"))
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.live_dir = self.base_dir / "live"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.live_dir.mkdir(parents=True, exist_ok=True)

    @property
    def provider_name(self) -> str:
        return "local"

    def _get_real_path(self, uri: str) -> Path:
        if uri.startswith("file://"):
            return Path(uri.replace("file://", ""))
        else:
            raise ValueError(f"Unsupported URI scheme in {uri}")

    def write_raw_documents(self, documents: List[RawDocument]) -> List[str]:
        saved_uris = []
        for doc in documents:
            filename = f"{doc.timestamp.strftime('%Y%m%d%H%M%S')}_{doc.source_type}.md"
            filepath = self.raw_dir / filename

            metadata: dict = {
                "doc_id": doc.doc_id,
                "source_type": doc.source_type,
                "source_id": doc.source_id,
                "timestamp": doc.timestamp.isoformat(),
                "tags": doc.tags,
                "visibility": str(doc.visibility),
            }
            if doc.source_url is not None:
                metadata["source_url"] = doc.source_url
            if doc.source_hash is not None:
                metadata["source_hash"] = doc.source_hash
            if doc.source_metadata is not None:
                metadata["source_metadata"] = doc.source_metadata.model_dump(
                    exclude_none=True
                )

            post = frontmatter.Post(doc.content, **metadata)
            filepath.write_text(frontmatter.dumps(post), encoding="utf-8")
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
        for filepath in self.raw_dir.glob(f"{prefix}*"):
            if filepath.is_file():
                uris.append(f"file://{filepath.absolute()}")
        return uris

    def get_raw_document_metadata(self, doc_id: str) -> RawDocument | None:
        for filepath in self.raw_dir.glob("*.md"):
            post = frontmatter.load(str(filepath))
            if post.metadata.get("doc_id") != doc_id:
                continue

            m = post.metadata
            raw_ts = m.get("timestamp")
            if isinstance(raw_ts, datetime):
                timestamp = raw_ts
            else:
                timestamp = datetime.fromisoformat(str(raw_ts))

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
        filename = f"{document_id}.md"
        filepath = self.live_dir / filename
        filepath.write_text(content, encoding="utf-8")
        return f"file://{filepath.absolute()}"

    def read_live_document(self, uri: str) -> str:
        filepath = self._get_real_path(uri)
        return filepath.read_text(encoding="utf-8")

    def list_live_documents(self, prefix: str = "") -> List[str]:
        uris = []
        for filepath in self.live_dir.glob(f"{prefix}*"):
            if filepath.is_file():
                uris.append(f"file://{filepath.absolute()}")
        return uris
