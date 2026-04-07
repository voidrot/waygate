from waygate_core.settings import get_runtime_settings
from waygate_storage.storage_registry import storage_registry

from mcp_server.service import BriefingService

storage_registry.discover_providers()
settings = get_runtime_settings()
storage = storage_registry.get_provider(settings.storage_provider)
briefing_service = BriefingService.from_storage(storage)
