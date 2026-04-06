from datetime import datetime, timezone
from compiler.config import storage
from compiler.state import GraphState

import logging

from waygate_core.doc_helpers import generate_frontmatter, slugify
from waygate_core.schemas import FrontMatterDocument

logger = logging.getLogger(__name__)


def publish_node(state: GraphState) -> dict:
    logger.info("--- PUBLISH: Writing file to live Wiki ---")

    topic = state["target_topic"]
    draft = state["current_draft"]
    sources_uris = state["new_document_uris"]

    timestamp = datetime.now(timezone.utc).isoformat()

    frontmatter = generate_frontmatter(
        FrontMatterDocument(
            title=topic,
            last_updated=timestamp,
            sources=sources_uris,
            tags=[],
            status="live",
        )
    )

    final_article = f"{frontmatter}\n{draft}"

    file_name = f"{slugify(topic)}.md"

    storage.write_live_document(file_name, final_article)

    return {"status": "completed"}
