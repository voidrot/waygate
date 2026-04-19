from __future__ import annotations

from waygate_workflows.schema import DraftGraphState
from waygate_workflows.tools.publishing import render_published_document


def render_publish_artifact(state: DraftGraphState) -> str:
    return render_published_document(state)


__all__ = ["render_publish_artifact"]
