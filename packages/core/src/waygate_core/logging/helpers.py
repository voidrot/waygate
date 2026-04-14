from typing import Any
import structlog


def get_logger(*args: Any, **initial_values: Any) -> Any:
    """
    Returns a structlog logger instance.
    """
    return structlog.get_logger(*args, **initial_values)


def get_wrapped_logger(task_logger):
    return structlog.wrap_logger(task_logger)
