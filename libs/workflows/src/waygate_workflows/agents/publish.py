from __future__ import annotations

from waygate_workflows.content.publishing import render_compiled_artifact
from waygate_workflows.schema import DraftGraphState


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
    return render_compiled_artifact(state, compiled_document_id=compiled_document_id)


__all__ = ["render_publish_artifact"]
