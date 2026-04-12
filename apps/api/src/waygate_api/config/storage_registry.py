from waygate_api.config.config_registry import core_config
from waygate_core.plugin import PluginRegistry, PluginGroups, StoragePlugin

storage_registry = PluginRegistry(PluginGroups.STORAGE, StoragePlugin)
storage_registry.register_plugins()

_storage = storage_registry.get(core_config.storage_plugin_name)

if _storage is None:
    raise ValueError(
        f"Storage plugin '{core_config.storage_plugin_name}' not found in registry."
    )
storage = _storage
