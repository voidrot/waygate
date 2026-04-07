import logging
from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from redis import Redis
from rq import Queue

from waygate_core.doc_helpers import infer_initial_topic
from waygate_core.plugin_base import RawDocument
from waygate_core.settings import get_runtime_settings
from receiver.core.config import storage

logger = logging.getLogger(__name__)

settings = get_runtime_settings()
redis_conn = Redis.from_url(settings.redis_url)

draft_queue = Queue(settings.draft_queue_name, connection=redis_conn)


def _build_initial_state(documents: List[RawDocument], saved_uris: List[str]) -> dict:
    return {
        "state_version": "1",
        "trace_id": str(uuid4()),
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
        "new_document_uris": saved_uris,
        "raw_documents_metadata": [doc.model_dump(mode="json") for doc in documents],
        "target_topic": infer_initial_topic(documents),
        "document_type": "concepts",
        "template_name": "default",
        "current_draft": None,
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "pending_draft",
    }


async def save_and_trigger_langgraph_async(documents: List[RawDocument]) -> None:
    if not documents:
        return

    logger.info(f"Received {len(documents)} documents. Writing to storage.")

    saved_uris = storage.write_raw_documents(documents)

    logger.info(f"Saved documents to storage with URIs: {saved_uris}")

    initial_state = _build_initial_state(documents, saved_uris)

    job = draft_queue.enqueue(
        "compiler.worker.execute_graph",
        initial_state,
        job_timeout="10m",  # LLM calls can take a while, give it a long timeout
    )

    logger.info(
        f"Enqueued LangGraph job with ID: {job.id} and initial state: {initial_state}"
    )
