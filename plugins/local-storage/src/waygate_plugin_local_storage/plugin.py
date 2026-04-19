from datetime import datetime, UTC
from waygate_plugin_local_storage import __VERSION__
from pathlib import Path
from pydantic import BaseModel, Field
from waygate_core.plugin.hooks import PluginConfigRegistration, hookimpl
from waygate_core.plugin.storage import (
    StorageInvalidNamespaceError,
    StorageNamespace,
    StoragePlugin,
)

PLUGIN_NAME = "local-storage"


class LocalStorageConfig(BaseModel):
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
        default=False,
        description="Whether to use soft delete (move to a deleted directory) instead of hard delete.",
    )
    keep_versioned: bool = Field(
        default=False,
        description="Whether to keep versioned copies of files when they are updated or deleted.",
    )


class LocalStoragePlugin(StoragePlugin):
    plugin_name = PLUGIN_NAME

    def __init__(self, config: LocalStorageConfig | None = None) -> None:
        self._config = config or LocalStorageConfig()
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

        self.namespace_dirs = {
            "raw": self.raw_dir,
            "staging": self.staging_dir,
            "review": self.review_dir,
            "published": self.publish_dir,
            "metadata": self.metadata_dir,
            "templates": self.templates_dir,
            "agents": self.agents_dir,
        }

        self._setup_storage()

    @staticmethod
    @hookimpl
    def waygate_storage_plugin() -> type["LocalStoragePlugin"]:
        return LocalStoragePlugin

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        return PluginConfigRegistration(name=PLUGIN_NAME, config=LocalStorageConfig)

    @property
    def name(self) -> str:
        return PLUGIN_NAME

    @property
    def description(self) -> str:
        return "A simple local storage plugin for WayGate."

    @property
    def version(self) -> str:
        return __VERSION__

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

    def _strip_prefix(self, uri: str) -> str:
        """
        Strip the file prefix from a URI if it exists.

        Args:
            uri (str): The URI to strip the prefix from.
        Returns:
            str: The absolute URI without the file prefix.
        """
        if uri.startswith(self._config.file_prefix):
            return uri[len(self._config.file_prefix) :]
        return uri

    def _build_storage_uri(self, path: Path) -> str:
        resolved_path = path.resolve()
        resolved_base_dir = self.base_dir.resolve()

        try:
            relative_path = resolved_path.relative_to(resolved_base_dir).as_posix()
        except ValueError:
            relative_path = resolved_path.as_posix()

        return f"{self._config.file_prefix}{relative_path}"

    def _build_path(self, document_path: str) -> Path:
        """
        Build a file system path based on the document path.

        Args:
            document_path (str): The relative path for the document within the namespace.
        Returns:
            Path: The full file system path for the document.
        """

        clean_doc_path = self._strip_prefix(document_path)

        return Path(self.base_dir / clean_doc_path)

    def _build_plugin_path(
        self, namespace: StorageNamespace, document_path: str
    ) -> str:
        """
        Build a file system path for soft-deleted documents based on the namespace and document path.

        Args:
            namespace (StorageNamespace): The namespace for the document (e.g. "raw", "staging").
            document_path (str): The relative path for the document within the namespace.
        Returns:
            str: The full soft path to the document.
        """

        return f"file://{namespace}/{document_path}"

    def _normalize_namespaced_document_path(
        self, document_path: str, namespace_dir: str
    ) -> str:
        cleaned_document_path = self._strip_prefix(document_path).lstrip("/")

        path_parts = Path(cleaned_document_path).parts
        if path_parts and path_parts[0] in self.namespace_dirs:
            path_parts = path_parts[1:]

        normalized_parts = (namespace_dir, *path_parts)
        return str(Path(self._config.base_path, *normalized_parts)).replace("\\", "/")

    def build_namespaced_path(
        self, namespace: StorageNamespace, document_path: str
    ) -> str:
        namespace_dirs = {
            StorageNamespace.Raw: self._config.raw_dir,
            StorageNamespace.Staging: self._config.staging_dir,
            StorageNamespace.Review: self._config.review_dir,
            StorageNamespace.Published: self._config.publish_dir,
            StorageNamespace.Metadata: self._config.metadata_dir,
            StorageNamespace.Templates: self._config.templates_dir,
            StorageNamespace.Agents: self._config.agents_dir,
        }

        try:
            base_dir = namespace_dirs[namespace]
        except KeyError as exc:
            raise StorageInvalidNamespaceError(
                f"Invalid storage namespace: {namespace}"
            ) from exc

        return self._normalize_namespaced_document_path(document_path, base_dir)

    def write_document(self, document_path: str, content: str) -> str:
        path = self._build_path(document_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return self._build_storage_uri(path)

    def read_document(self, document_path: str) -> str:
        path = self._build_path(document_path)
        return path.read_text()

    def list_documents(self, search_path: str, prefix: str = "") -> list[str]:
        root = self._build_path(search_path)

        if not root.exists():
            return []

        if root.is_file():
            rel = self._build_storage_uri(root)
            if prefix and not rel.startswith(prefix):
                return []
            return [rel]

        matches: list[str] = []
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            rel = self._build_storage_uri(file_path)
            if prefix and not rel.startswith(prefix):
                continue
            matches.append(rel)

        return sorted(matches)

    def delete_document(self, document_path: str) -> None:
        path = self._build_path(document_path)
        if not path.exists() or not path.is_file():
            return

        if self.keep_versioned:
            timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
            versioned_target = (
                self.versioned_dir / f"{self._strip_prefix(document_path)}.{timestamp}"
            )
            versioned_target.parent.mkdir(parents=True, exist_ok=True)
            versioned_target.write_text(path.read_text())

        if self.soft_delete:
            deleted_target = self.deleted_dir / self._strip_prefix(document_path)
            deleted_target.parent.mkdir(parents=True, exist_ok=True)
            path.replace(deleted_target)
            return

        path.unlink()
