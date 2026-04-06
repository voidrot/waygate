import logging
import os
from typing import List
from redis import Redis
from rq import Queue

from waygate_core.plugin_base import RawDocument
from receiver.core.config import storage

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(REDIS_URL)


draft_queue = Queue("draft_tasks", connection=redis_conn)


async def save_and_trigger_langgraph_async(documents: List[RawDocument]) -> None:
    if not documents:
        return

    logger.info(f"Received {len(documents)} documents. Writing to storage.")

    saved_uris = storage.write_raw_documents(documents)

    logger.info(f"Saved documents to storage with URIs: {saved_uris}")

    initial_state = {
        "new_document_uris": saved_uris,
        "target_topic": "Auto-Detect",  # We can have the LLM figure this out later
        "revision_count": 0,
        "status": "pending_draft",
    }

    job = draft_queue.enqueue(
        "compiler.worker.execute_graph",
        initial_state,
        job_timeout="10m",  # LLM calls can take a while, give it a long timeout
    )

    logger.info(
        f"Enqueued LangGraph job with ID: {job.id} and initial state: {initial_state}"
    )
