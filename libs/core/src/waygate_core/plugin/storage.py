"""Storage plugin contracts and namespace helpers."""

from enum import StrEnum
from typing import List
from abc import ABC, abstractmethod


class StorageInvalidNamespaceError(ValueError):
    """Raised when an invalid namespace is used for storage operations."""


class StorageNamespace(StrEnum):
    """Defines valid namespaces for storage operations."""

    Raw = "raw"
    Staging = "staging"
    Review = "review"
    Compiled = "compiled"
    Published = "published"
    Metadata = "metadata"
    Templates = "templates"
    Agents = "agents"


class StoragePlugin(ABC):
    """Base class for storage plugins.

    Storage plugins are instantiated once at startup and cached process-wide.
    Implement storage operations as thread-safe; the same plugin instance may be
    called concurrently by multiple application components.
    """

    plugin_group: str = "waygate.plugins.storage"
    hook_name: str = "waygate_storage_plugin"

    @property
    def name(self) -> str:
        """Return the plugin name.

        Returns:
            The plugin name.
        """
        return self.__class__.__name__

    @property
    def description(self) -> str:
        """Return a brief plugin description.

        Returns:
            The plugin description.
        """
        return "No description provided."

    @property
    def version(self) -> str:
        """Return the plugin version.

        Returns:
            The plugin version.
        """
        return "0.0.0"

    @abstractmethod
    def build_namespaced_path(
        self, namespace: StorageNamespace, document_path: str
    ) -> str:
        """Build a namespaced path for a document.

        Args:
            namespace: The storage namespace.
            document_path: The original document path.

        Returns:
            The namespaced document path.
        """
        raise NotImplementedError(
            "Storage plugins must implement the build_namespaced_path method."
        )

    @abstractmethod
    def write_document(self, document_path: str, content: str) -> str:
        """Write a document to storage.

        Args:
            document_path: The path where the document should be stored.
            content: The content of the document.

        Returns:
            The stored document URI.
        """
        raise NotImplementedError(
            "Storage plugins must implement the write_document method."
        )

    def write_documents(self, documents: List[tuple[str, str]]) -> List[str]:
        """Write multiple documents to storage.

        Args:
            documents: A list of ``(document_path, content)`` tuples.

        Returns:
            A list of stored document URIs.
        """
        paths = []
        for document_path, content in documents:
            paths.append(self.write_document(document_path, content))
        return paths

    @abstractmethod
    def read_document(self, document_path: str) -> str:
        """Read a document from storage.

        Args:
            document_path: The path where the document is stored.

        Returns:
            The document content.
        """
        raise NotImplementedError(
            "Storage plugins must implement the read_document method."
        )

    def read_documents(self, documents: List[str]) -> List[str]:
        """Read multiple documents from storage.

        Args:
            documents: A list of document paths to read.

        Returns:
            A list of document contents.
        """
        docs = []
        for document_path in documents:
            # The current contract keeps the return shape simple for callers.
            docs.append(self.read_document(document_path))
        return docs

    @abstractmethod
    def list_documents(self, search_path: str, prefix: str = "") -> list[str]:
        """List documents under a search path.

        Args:
            search_path: The namespace or root path to search.
            prefix: Optional prefix filter.

        Returns:
            A list of matching document paths.
        """
        raise NotImplementedError(
            "Storage plugins must implement the list_documents method."
        )

    @abstractmethod
    def delete_document(self, document_path: str) -> None:
        """Delete a document from storage.

        Args:
            document_path: The path where the document is stored.
        """
        raise NotImplementedError(
            "Storage plugins must implement the delete_document method."
        )

    def delete_documents(self, documents: List[str]) -> None:
        """Delete multiple documents from storage.

        Args:
            documents: A list of document paths to delete.
        """
        for document_path in documents:
            self.delete_document(document_path)
