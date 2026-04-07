from waygate_storage.storage_registry import storage_registry
from waygate_core.settings import get_runtime_settings

storage_registry.discover_providers()
settings = get_runtime_settings()
storage = storage_registry.get_provider(settings.storage_provider)
