from waygate_core.plugin import PluginRegistry, PluginGroups, StoragePlugin
from waygate_core.config.schema import CoreSettings
from waygate_core.config import ConfigRegistry

config_registry = ConfigRegistry()
config_registry.discover()

_core_config: CoreSettings | None = config_registry.get("core")
core_config = _core_config if _core_config is not None else CoreSettings()


storage_registry = PluginRegistry(PluginGroups.STORAGE, StoragePlugin)
storage_registry.register_plugins()

_storage = storage_registry.get(core_config.storage_plugin_name)
storage = (
    _storage
    if _storage is not None
    else (
        lambda: (_ for _ in ()).throw(
            ValueError(
                f"Storage plugin '{core_config.storage_plugin_name}' not found in registry"
            )
        )
    )()
)
