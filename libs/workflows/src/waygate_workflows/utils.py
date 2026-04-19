from waygate_core import get_app_context
from waygate_core.plugin import StoragePlugin


def resolve_storage() -> StoragePlugin:
    app_context = get_app_context()
    return app_context.plugins.storage[app_context.config.core.storage_plugin_name]
