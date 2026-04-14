from abc import abstractmethod
from typing import List
from enum import StrEnum
from waygate_core.plugin.base import WayGatePluginBase


class StorageInvalidNamespaceError(ValueError):
    """Raised when an invalid namespace is used for storage operations."""


class StorageNamespace(StrEnum):
    """Defines valid namespaces for storage operations."""

    Raw = "raw"
    Staging = "staging"
    Review = "review"
    Published = "published"
    Metadata = "metadata"
    Templates = "templates"
    Agents = "agents"


class StoragePlugin(WayGatePluginBase):
    """
    Base class for storage plugins.

    Storage plugins are instantiated once at startup and cached process-wide.
    Implement storage operations as thread-safe; the same plugin instance may be
    called concurrently by multiple application components.
    """

    plugin_group: str = "waygate.plugins.storage"
    hook_name: str = "waygate_storage_plugin"

    @abstractmethod
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
        raise NotImplementedError(
            "Storage plugins must implement the build_namespaced_path method."
        )

    @abstractmethod
    def write_document(self, document_path: str, content: str) -> str:
        """
        Write a document to storage.

        Args:
            namespace (StorageNamespace): The namespace for the document.
            document_path (str): The path where the document should be stored.
            content (str): The content of the document.
        """
        raise NotImplementedError(
            "Storage plugins must implement the write_document method."
        )

    def write_documents(self, documents: List[tuple[str, str]]) -> List[str]:
        """
        Write multiple documents to storage.

        Args:
            documents (List[tuple[str, str]]): A list of tuples containing the document path and content for each document to write.
        """
        paths = []
        for document_path, content in documents:
            paths.append(self.write_document(document_path, content))
        return paths

    @abstractmethod
    def read_document(self, document_path: str) -> str:
        """
        Read a document from storage.

        Args:
            document_path (str): The path where the document is stored.

        Returns:
            RawDocument: The content of the document.
        """
        raise NotImplementedError(
            "Storage plugins must implement the read_document method."
        )

    def read_documents(self, documents: List[str]) -> List[str]:
        """
        Read multiple documents from storage.

        Args:
            documents (List[tuple[StorageNamespace, str]]): A list of tuples containing the namespace and document path for each document to read.

        Returns:
            List[RawDocument]: A list of RawDocument instances containing the content of each document.
        """
        docs = []
        for document_path in documents:
            # TODO: we should probably return a tuple with the document path and content, or a custom object that includes metadata about the document along with the content, instead of just returning the raw content, but for now we'll just return the raw content
            docs.append(self.read_document(document_path))
        return docs

    @abstractmethod
    def list_documents(self, search_path: str, prefix: str = "") -> list[str]:
        """
        List documents in a given namespace with an optional prefix filter.

        Args:
            namespace (StorageNamespace): The namespace to list documents from.
            prefix (str, optional): A prefix to filter document paths. Defaults to "".

        Returns:
            list[str]: A list of document paths matching the criteria.
        """
        raise NotImplementedError(
            "Storage plugins must implement the list_documents method."
        )

    @abstractmethod
    def delete_document(self, document_path: str) -> None:
        """
        Delete a document from storage.

        Args:
            document_path (str): The path where the document is stored.
        """
        raise NotImplementedError(
            "Storage plugins must implement the delete_document method."
        )

    def delete_documents(self, documents: List[str]) -> None:
        """
        Delete multiple documents from storage.

        Args:
            documents (List[tuple[StorageNamespace, str]]): A list of tuples containing the namespace and document path for each document to delete.
        """
        for document_path in documents:
            self.delete_document(document_path)
