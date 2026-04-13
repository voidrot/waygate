from waygate_core.plugin.storage_base import (
    StorageNamespace,
)
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
        default=False,
        description="Whether to use soft delete (move to a deleted directory) instead of hard delete.",
    )
    keep_versioned: bool = Field(
        default=False,
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

    def _strip_prefix(self, uri: str) -> str:
        """
        Strip the file prefix from a URI if it exists.

        Args:
            uri (str): The URI to strip the prefix from.
        Returns:
            str: The absolute URI without the file prefix.
        """
        if uri.startswith(self._config.file_prefix):
            stripped = uri[len(self._config.file_prefix) :]
            return stripped.lstrip("/") if stripped.startswith("/") else stripped
        if uri.startswith("/"):
            return uri.lstrip("/")
        return uri

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

    def build_namespaced_path(
        self, namespace: StorageNamespace, document_path: str
    ) -> str:
        """
        Build a namespaced path for a document.

        Args:
            namespace (StorageNamespace): The namespace for the document.
            document_path (str): The original document path.
        Returns:
            str: The namespaced document path.
        """
        # make sure that path is not already namespaced
        cleaned_path = self._strip_prefix(document_path)
        is_namespaced = any(
            cleaned_path.startswith(f"{ns}/") for ns in self.namespace_dirs.keys()
        )
        if is_namespaced:
            raise ValueError(
                f"Document path '{document_path}' appears to already be namespaced."
            )
        return f"{namespace}/{cleaned_path}"

    def write_document(self, document_path: str, content: str) -> str:
        path = self._build_path(document_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return f"file://{self._strip_prefix(document_path)}"

    def read_document(self, document_path: str) -> str:
        path = self._build_path(document_path)
        return path.read_text()
