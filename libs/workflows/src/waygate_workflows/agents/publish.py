from __future__ import annotations

from waygate_core.logging import get_logger

from waygate_workflows.content.publishing import render_compiled_artifact
from waygate_workflows.schema import DraftGraphState

logger = get_logger(__name__)


def render_publish_artifact(
    state: DraftGraphState,
    *,
    compiled_document_id: str,
) -> str:
    """Render the compiled artifact for the current draft state.

    Args:
        state: Draft workflow state at the publish boundary.
        compiled_document_id: Stable hash id for the compiled artifact.

    Returns:
        Markdown document string ready to write to storage.
    """
    logger.debug(
        "Rendering publish artifact",
        source_set_key=state.get("source_set_key"),
        compiled_document_id=compiled_document_id,
        draft_length=len(state["current_draft"]),
    )
    artifact = render_compiled_artifact(
        state, compiled_document_id=compiled_document_id
    )
    logger.debug(
        "Rendered publish artifact",
        source_set_key=state.get("source_set_key"),
        compiled_document_id=compiled_document_id,
        artifact_length=len(artifact),
    )
    return artifact


__all__ = ["render_publish_artifact"]
