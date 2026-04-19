import logging

import structlog


def get_log_level():
    """
    Get the log level from the environment variable LOG_LEVEL, defaulting to INFO.
    """
    import os

    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, log_level_str, logging.INFO)


def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(get_log_level()),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
