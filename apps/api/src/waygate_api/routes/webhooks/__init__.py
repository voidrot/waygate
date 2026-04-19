__all__ = ["webhook_router"]


def __getattr__(name: str):
    if name == "webhook_router":
        from .router import webhook_router

        return webhook_router
    raise AttributeError(name)
