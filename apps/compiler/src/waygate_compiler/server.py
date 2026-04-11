from rq import Worker
from waygate_compiler.registry import core_config
from redis import Redis
from waygate_core.logging import configure_logging, get_logger

configure_logging()

logger = get_logger()


def main() -> None:
    redis_conn = Redis.from_url(str(core_config.redis_dsn))
    draft_queue = core_config.draft_queue_name
    worker = Worker([draft_queue], connection=redis_conn)
    logger.info("Waygate Compiler Worker is running...")
    worker.work()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt, SystemExit:
        pass
