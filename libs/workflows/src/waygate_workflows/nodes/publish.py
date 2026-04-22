from __future__ import annotations

from waygate_core.files import compute_content_hash
from waygate_core.plugin import StorageNamespace

from waygate_workflows.agents.publish import render_publish_artifact
from waygate_workflows.runtime.storage import resolve_storage
from waygate_workflows.schema import DraftGraphState, DraftWorkflowStatus


def publish_draft(state: DraftGraphState) -> dict[str, object]:
    """Write the approved compile artifact to storage.

    Args:
        state: Draft workflow state at the publish boundary.

    Returns:
        Partial state update containing the compiled artifact identity.

    Raises:
        ValueError: If the source-set key is missing.
    """
    source_set_key = state.get("source_set_key")
    if not source_set_key:
        raise ValueError("Publish requires a source_set_key")

    compiled_document_hash = compute_content_hash(state["current_draft"])
    storage = resolve_storage()
    document_path = storage.build_namespaced_path(
        StorageNamespace.Compiled,
        f"{compiled_document_hash}.md",
    )
    document_uri = storage.write_document(
        document_path,
        render_publish_artifact(
            state,
            compiled_document_id=compiled_document_hash,
        ),
    )
    return {
        "compiled_document_id": compiled_document_hash,
        "compiled_document_uri": document_uri,
        "compiled_document_hash": compiled_document_hash,
        "status": DraftWorkflowStatus.APPROVED,
    }
