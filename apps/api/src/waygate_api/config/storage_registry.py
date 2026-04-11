from waygate_core.plugin import PluginRegistry, PluginGroups, StoragePlugin

storage_registry = PluginRegistry(PluginGroups.STORAGE, StoragePlugin)
storage_registry.register_plugins()
