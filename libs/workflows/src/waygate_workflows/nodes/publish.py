from __future__ import annotations

from waygate_core.plugin import StorageNamespace

from waygate_workflows.agents.publish import render_publish_artifact
from waygate_workflows.schema import DraftGraphState, DraftWorkflowStatus
from waygate_workflows.utils import resolve_storage


def publish_draft(state: DraftGraphState) -> dict[str, object]:
    """Write the published markdown artifact to storage.

    Args:
        state: Draft workflow state at the publish boundary.

    Returns:
        Partial state update containing the published artifact identity.

    Raises:
        ValueError: If the source-set key is missing.
    """
    source_set_key = state.get("source_set_key")
    if not source_set_key:
        raise ValueError("Publish requires a source_set_key")

    storage = resolve_storage()
    document_path = storage.build_namespaced_path(
        StorageNamespace.Published,
        f"{source_set_key}.md",
    )
    document_uri = storage.write_document(document_path, render_publish_artifact(state))
    return {
        "published_document_id": source_set_key,
        "published_document_uri": document_uri,
        "status": DraftWorkflowStatus.PUBLISHED,
    }
