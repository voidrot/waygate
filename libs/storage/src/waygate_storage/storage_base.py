from abc import ABC, abstractmethod
from typing import List

from waygate_core.plugin_base import RawDocument


class StorageProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def write_raw_documents(self, documents: List[RawDocument]) -> List[str]:
        """Save a batch of raw documents to the storage backend.

        Args:
            documents: a list of `RawDocument` instances to be saved.

        Returns:
            A list of unique document IDs assigned by the storage system.
        """

        pass

    @abstractmethod
    def read_raw_document(self, uri: str) -> str:
        """Retrieve a single raw document by its unique ID.

        Args:
            uri: the path to the document.

        Returns:
            The content of the document as a string.
        """

        pass

    @abstractmethod
    def delete_raw_document(self, uri: str) -> None:
        """Delete a single raw document by its unique ID.

        Args:
            uri: the path to the document to be deleted.

        Returns:
            None
        """

        pass

    @abstractmethod
    def list_raw_documents(self, prefix: str = "") -> List[str]:
        """List all document URIs in the storage backend, optionally filtered by a prefix.

        Args:
            prefix: an optional string to filter document URIs.
        Returns:
            A list of document URIs that match the prefix filter.
        """

        pass

    @abstractmethod
    def write_live_document(self, document_id: str, content: str) -> str:
        """Save a live document to the storage backend.

        Args:
            document_id: a unique identifier for the live document.
            content: the content of the live document to be saved.

        Returns:
            The URI of the saved live document.
        """

        pass

    @abstractmethod
    def read_live_document(self, uri: str) -> str:
        """Retrieve a single live document by its unique ID.

        Args:
            uri: the path to the live document.

        Returns:
            The content of the live document as a string.
        """

        pass

    @abstractmethod
    def list_live_documents(self, prefix: str = "") -> List[str]:
        """List all live document URIs in the storage backend, optionally filtered by a prefix.

        Args:
            prefix: an optional string to filter live document URIs.
        Returns:
            A list of live document URIs that match the prefix filter.
        """

        pass

    def write_staging_document(self, document_id: str, content: str) -> str:
        """Save a dead-letter staging document to the storage backend.

        Storage providers that support dead-letter escalation should override
        this method. The base implementation fails explicitly.
        """

        raise NotImplementedError("This storage provider does not support staging")

    @abstractmethod
    def get_raw_document_metadata(self, doc_id: str) -> RawDocument | None:
        """Retrieve a raw document's metadata by its canonical doc_id.

        Parses the stored frontmatter to reconstruct metadata fields without
        requiring the caller to re-parse the full document content. Returns
        ``None`` if no document with the given ``doc_id`` is found.

        Args:
            doc_id: the globally unique document ID assigned at ingest time.

        Returns:
            A ``RawDocument`` instance populated from stored frontmatter, or
            ``None`` if the document does not exist.
        """

        pass
