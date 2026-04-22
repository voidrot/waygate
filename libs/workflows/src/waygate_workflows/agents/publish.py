from __future__ import annotations

from waygate_workflows.content.publishing import render_published_document
from waygate_workflows.schema import DraftGraphState


def render_publish_artifact(state: DraftGraphState) -> str:
    """Render the published artifact for the current draft state.

    Args:
        state: Draft workflow state at the publish boundary.

    Returns:
        Markdown document string ready to write to storage.
    """
    return render_published_document(state)


__all__ = ["render_publish_artifact"]
