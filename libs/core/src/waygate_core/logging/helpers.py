"""Convenience wrappers around structlog logger creation."""

from typing import Any
import structlog


def get_logger(*args: Any, **initial_values: Any) -> Any:
    """Return a structlog logger instance.

    Args:
        *args: Positional arguments forwarded to ``structlog.get_logger``.
        **initial_values: Keyword arguments forwarded to
            ``structlog.get_logger``.

    Returns:
        A structlog logger instance.
    """

    return structlog.get_logger(*args, **initial_values)


def get_wrapped_logger(task_logger):
    """Wrap an existing logger with structlog.

    Args:
        task_logger: The logger to wrap.

    Returns:
        A structlog-wrapped logger.
    """

    return structlog.wrap_logger(task_logger)
