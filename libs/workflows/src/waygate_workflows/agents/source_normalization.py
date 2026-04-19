from __future__ import annotations

from waygate_workflows.schema import OrderedDocumentRef
from waygate_workflows.schema import SourceDocumentState
from waygate_workflows.tools.documents import derive_source_set_key
from waygate_workflows.tools.documents import parse_source_document
from waygate_workflows.tools.documents import to_ordered_document_ref
from waygate_workflows.utils import resolve_storage


def normalize_source_documents(
    raw_document_uris: list[str],
) -> tuple[list[SourceDocumentState], list[OrderedDocumentRef], str]:
    """Read and normalize all raw source documents for a compile request.

    Args:
        raw_document_uris: Storage URIs received from the workflow trigger.

    Returns:
        Tuple of parsed source documents, durable ordering references, and the
        derived source-set key.
    """
    storage = resolve_storage()
    source_documents = [
        parse_source_document(document_uri, storage.read_document(document_uri))
        for document_uri in raw_document_uris
    ]
    document_order = [
        to_ordered_document_ref(document) for document in source_documents
    ]
    source_set_key = derive_source_set_key(source_documents)
    return source_documents, document_order, source_set_key


__all__ = ["normalize_source_documents"]
