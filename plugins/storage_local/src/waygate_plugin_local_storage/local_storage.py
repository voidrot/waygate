from typing import List

from waygate_storage.storage_base import StorageProvider
from pathlib import Path
import os
from waygate_core.plugin_base import RawDocument


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
            with filepath.open("w", encoding="utf-8") as f:
                # TODO: Move metadata to a function so that it can be reused by other plugins
                f.write("---\n")
                f.write(f"source: {doc.source_type}\n")
                f.write(f"id: {doc.source_id}\n")
                f.write(f"tags: {doc.tags}\n")
                f.write("---\n")
                f.write(doc.content)
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
