from typing import Iterable
from waygate_core.schema import RawDocument
from pathlib import Path
from pydantic import Field
from . import __version__
from waygate_core.plugin import StoragePlugin
from pydantic_settings import BaseSettings, SettingsConfigDict


class LocalStorageConfig(BaseSettings):
    """
    Configuration for the Local Storage plugin.
    """

    file_prefix: str = "file://"
    base_path: str = Field(
        default="wiki", description="Base path for local storage files."
    )
    raw_dir: str = Field(
        default="raw", description="Directory for raw files within the base path."
    )
    staging_dir: str = Field(
        default="staging",
        description="Directory for staging files within the base path.",
    )
    review_dir: str = Field(
        default="review",
        description="Directory for files needing review within the base path.",
    )
    publish_dir: str = Field(
        default="published",
        description="Directory for published files within the base path.",
    )
    metadata_dir: str = Field(
        default="metadata",
        description="Directory for metadata files within the base path.",
    )
    templates_dir: str = Field(
        default="templates",
        description="Directory for template files within the base path.",
    )
    agents_dir: str = Field(
        default="agents",
        description="Directory for agent files within the base path.",
    )
    soft_delete: bool = Field(
        default=True,
        description="Whether to use soft delete (move to a deleted directory) instead of hard delete.",
    )
    keep_versioned: bool = Field(
        default=True,
        description="Whether to keep versioned copies of files when they are updated or deleted.",
    )

    model_config = SettingsConfigDict(env_prefix="waygate_local_storage_")


class LocalStorageProvider(StoragePlugin):
    def __init__(self):
        self._config = LocalStorageConfig()
        self.base_dir = Path(self._config.base_path)
        self.raw_dir = self.base_dir / self._config.raw_dir
        self.staging_dir = self.base_dir / self._config.staging_dir
        self.review_dir = self.base_dir / self._config.review_dir
        self.publish_dir = self.base_dir / self._config.publish_dir
        self.metadata_dir = self.base_dir / self._config.metadata_dir
        self.templates_dir = self.base_dir / self._config.templates_dir
        self.agents_dir = self.base_dir / self._config.agents_dir
        self.versioned_dir = self.base_dir / "versioned"
        self.deleted_dir = self.base_dir / "deleted"
        self.soft_delete = self._config.soft_delete
        self.keep_versioned = self._config.keep_versioned

        self._setup_storage()

    @property
    def name(self) -> str:
        return "local-storage"

    @property
    def description(self) -> str:
        return "A simple local storage plugin for WayGate."

    @property
    def version(self) -> str:
        return __version__

    @property
    def config(self) -> BaseSettings:

        return self._config

    def _setup_storage(self) -> None:
        """
        Set up the necessary directories for local storage.
        """
        for directory in [
            self.raw_dir,
            self.staging_dir,
            self.review_dir,
            self.publish_dir,
            self.metadata_dir,
            self.templates_dir,
            self.agents_dir,
            self.versioned_dir if self.keep_versioned else None,
            self.deleted_dir if self.soft_delete else None,
        ]:
            if directory is not None:
                directory.mkdir(parents=True, exist_ok=True)

    def _get_real_path(self, uri: str) -> Path:
        """
        Convert a file path with the file prefix to a real file system path.

        Args:
            uri (str): The file URI to convert.
        Returns:
            Path: The real file system path corresponding to the given URI.
        """
        if uri.startswith(self._config.file_prefix):
            return self.base_dir / uri.replace(self._config.file_prefix, "")

        normalized_uri = uri.strip("/")

        namespaced_roots = {
            "raw": self.raw_dir,
            "staging": self.staging_dir,
            "review": self.review_dir,
            "published": self.publish_dir,
            "metadata": self.metadata_dir,
            "templates": self.templates_dir,
            "agents": self.agents_dir,
            "versioned": self.versioned_dir,
            "deleted": self.deleted_dir,
        }

        for namespace, root_dir in namespaced_roots.items():
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

    def _write_file(self, path: Path, content: str) -> None:
        """
        Write content to a file, creating parent directories if necessary.

        Args:
            path (Path): The file path to write to.
            content (str): The content to write to the file.
        """
        if self.keep_versioned and path.exists():
            versioned_path = self.versioned_dir / path.relative_to(self.base_dir)
            versioned_path.parent.mkdir(parents=True, exist_ok=True)
            path.rename(versioned_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def _read_file(self, path: Path) -> str:
        """Read content from a file.

        Args:
            path (Path): The file path to read from.
        Returns:
            str: The content of the file.
        """
        return path.read_text()

    def _delete_file(self, path: Path) -> None:
        """Delete a file, either by moving it to a deleted directory or by removing it.

        Args:
            path (Path): The file path to delete.
        """
        if self.soft_delete:
            deleted_path = self.deleted_dir / path.relative_to(self.base_dir)
            deleted_path.parent.mkdir(parents=True, exist_ok=True)
            path.rename(deleted_path)
        else:
            path.unlink()

    def write_raw_document(self, document: RawDocument) -> None:
        path = (
            self.raw_dir
            / f"{document.timestamp.strftime('%Y%m%d%H%M%S')}_{document.doc_id}.md"
        )
        self._write_file(path, document.content)

    def write_raw_documents(self, documents: list[RawDocument]) -> None:
        for document in documents:
            self.write_raw_document(document)

    def read_raw_document(self, uri: str) -> str:
        path = self._get_real_path(uri)
        return self._read_file(path)

    def delete_raw_document(self, uri: str) -> None:
        path = self._get_real_path(uri)
        self._delete_file(path)
