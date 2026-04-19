"""Webhook route package for the WayGate API app."""

__all__ = ["webhook_router"]


def __getattr__(name: str):
    """Lazily import the webhook router to avoid eager plugin loading.

    Args:
        name: The attribute name being requested.

    Returns:
        The webhook router when ``name`` is ``webhook_router``.

    Raises:
        AttributeError: If the requested attribute is unknown.
    """

    if name == "webhook_router":
        from .router import webhook_router

        return webhook_router
    raise AttributeError(name)
