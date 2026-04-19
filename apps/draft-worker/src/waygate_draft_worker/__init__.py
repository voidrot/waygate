from __future__ import annotations

from redis import Redis
from rq import Queue, Worker

from waygate_core import bootstrap_app
from waygate_core.logging import get_logger

__VERSION__ = "0.1.0"  # x-release-please-version

logger = get_logger(__name__)


def _resolve_runtime(app_context) -> tuple[str, str]:
    rq_config = getattr(app_context.config, "communication_rq", None)
    if rq_config is None:
        raise RuntimeError(
            "communication-rq configuration is unavailable; install and configure the plugin before starting the draft worker"
        )

    redis_url = rq_config.redis_url or str(app_context.config.core.redis_dsn)
    return redis_url, rq_config.draft_queue_name


def main() -> None:
    app_context = bootstrap_app()
    redis_url, queue_name = _resolve_runtime(app_context)

    connection = Redis.from_url(redis_url)
    queue = Queue(queue_name, connection=connection)
    worker = Worker([queue], connection=connection)

    logger.info("Starting draft worker", queue_name=queue_name)
    worker.work(with_scheduler=False)
