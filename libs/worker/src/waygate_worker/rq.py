from __future__ import annotations

from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue, Worker

from waygate_core.logging import get_logger
from waygate_workflows.router import process_workflow_trigger

logger = get_logger(__name__)


class RQWorkerConfig(BaseModel):
    """Configuration for the RQ-backed worker runtime."""

    redis_url: str
    draft_queue_name: str = Field(default="draft")
    cron_queue_name: str = Field(default="cron")
    with_scheduler: bool = Field(default=False)


def process_rq_workflow_trigger(payload: dict[str, object] | str) -> dict[str, object]:
    """Run the shared workflow trigger router from an RQ job."""

    return process_workflow_trigger(payload)


def run_rq_worker(config: RQWorkerConfig) -> None:
    """Start the Redis/RQ worker loop for workflow trigger queues."""

    connection = Redis.from_url(config.redis_url)
    queue_names = list(dict.fromkeys([config.draft_queue_name, config.cron_queue_name]))
    queues = [Queue(name, connection=connection) for name in queue_names]
    worker = Worker(queues, connection=connection)

    logger.info("Starting RQ worker", queue_names=queue_names)
    worker.work(with_scheduler=config.with_scheduler)
