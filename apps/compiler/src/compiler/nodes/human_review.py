from datetime import datetime, timezone
import logging

from compiler.config import storage
from compiler.state import GraphState
from waygate_core.doc_helpers import generate_frontmatter, slugify
from waygate_core.schemas import FrontMatterDocument, SourceType, Visibility

logger = logging.getLogger(__name__)


def human_review_node(state: GraphState) -> dict:
    logger.warning(
        "Escalating trace_id=%s after %s revisions; writing dead-letter artifact",
        state.get("trace_id"),
        state.get("revision_count"),
    )

    topic = state["target_topic"]
    draft = state.get("current_draft") or ""
    timestamp = datetime.now(timezone.utc).isoformat()

    metadata = FrontMatterDocument(
        title=f"Escalated: {topic}",
        last_compiled=timestamp,
        last_updated=timestamp,
        source_type=SourceType.SYNTHESIS,
        sources=state.get("new_document_uris", []),
        tags=["dead-letter", "escalated"],
        status="draft",
        visibility=Visibility.INTERNAL,
    )

    frontmatter = generate_frontmatter(metadata)
    body = (
        f"{frontmatter}\n"
        "## Escalation Context\n"
        f"- trace_id: {state.get('trace_id')}\n"
        f"- state_version: {state.get('state_version')}\n"
        f"- revision_count: {state.get('revision_count')}\n"
        f"- enqueued_at: {state.get('enqueued_at')}\n"
        f"- last_feedback: {state.get('qa_feedback') or 'n/a'}\n\n"
        "## Draft Snapshot\n"
        f"{draft}\n"
    )

    doc_name = f"{slugify(topic)}-{state.get('trace_id', 'unknown')}"
    staging_uri = storage.write_staging_document(doc_name, body)

    return {
        "status": "escalated",
        "staging_uri": staging_uri,
    }
