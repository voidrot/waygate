from __future__ import annotations

from datetime import UTC, datetime

import frontmatter

from waygate_workflows.schema import DocumentMetadataState
from waygate_workflows.schema import DraftGraphState
from waygate_workflows.tools.common import normalize_string_list


def aggregate_metadata(
    metadata_entries: list[DocumentMetadataState],
) -> dict[str, list[str]]:
    """Aggregate per-document metadata into published frontmatter fields.

    Args:
        metadata_entries: Per-document metadata collected during compile.

    Returns:
        Deduplicated metadata grouped by published frontmatter field.
    """
    aggregated = {
        "tags": [],
        "topics": [],
        "people": [],
        "organizations": [],
        "projects": [],
    }
    for entry in metadata_entries:
        for key in aggregated:
            aggregated[key].extend(entry.get(key, []))
    return {key: normalize_string_list(values) for key, values in aggregated.items()}


def render_published_document(state: DraftGraphState) -> str:
    """Render the final published markdown document with frontmatter.

    Args:
        state: Draft workflow state at the publish boundary.

    Returns:
        Markdown document string with compiled frontmatter.
    """
    aggregated = aggregate_metadata(state["extracted_metadata"])
    metadata = {
        "doc_id": state["source_set_key"],
        "source_set_key": state["source_set_key"],
        "source_documents": [doc["uri"] for doc in state["source_documents"]],
        "source_hashes": normalize_string_list(
            [doc.get("source_hash") for doc in state["source_documents"]]
        ),
        "source_uris": normalize_string_list(
            [doc.get("source_uri") for doc in state["source_documents"]]
        ),
        "compiled_at": datetime.now(tz=UTC).isoformat(),
        "review_feedback": state["review_feedback"],
        **aggregated,
    }
    document = frontmatter.Post(state["current_draft"])
    document.metadata.update(metadata)
    return frontmatter.dumps(document)
