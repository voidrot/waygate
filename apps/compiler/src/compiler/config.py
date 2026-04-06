from waygate_storage.storage_registry import storage_registry

storage_registry.discover_providers()

storage = storage_registry.get_provider()
