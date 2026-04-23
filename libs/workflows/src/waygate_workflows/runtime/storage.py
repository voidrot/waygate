from waygate_core.logging import get_logger
from waygate_core import get_app_context
from waygate_core.plugin import StoragePlugin

logger = get_logger(__name__)


def resolve_storage() -> StoragePlugin:
    """Resolve the configured storage plugin from the shared app context.

    Returns:
        Active storage plugin instance for the current process.
    """
    app_context = get_app_context()
    plugin_name = app_context.config.core.storage_plugin_name
    logger.debug("Resolving storage plugin", storage_plugin_name=plugin_name)
    storage = app_context.plugins.storage[plugin_name]
    logger.debug(
        "Resolved storage plugin",
        storage_plugin_name=plugin_name,
        plugin_type=type(storage).__name__,
    )
    return storage
