from typing import Dict
import importlib.metadata
import logging
from waygate_storage.storage_base import StorageProvider
import os

logger = logging.getLogger(__name__)


class StorageRegistry:
    def __init__(self):
        self._providers: Dict[str, type[StorageProvider]] = {}

    def discover_providers(self):
        entry_points = importlib.metadata.entry_points(group="waygate.plugins.storage")
        logger.info(
            f"Discovering storage providers from entry points: {[ep.name for ep in entry_points]}"
        )
        for ep in entry_points:
            try:
                provider_class = ep.load()
                temp_instance = provider_class()
                self._providers[temp_instance.provider_name] = provider_class
                logger.info(
                    "Discovered storage provider: %s", temp_instance.provider_name
                )
            except Exception as e:
                logger.exception("Failed to load storage provider %s: %s", ep.name, e)

    def get_provider(self) -> StorageProvider:
        active_name = os.getenv("STORAGE_PROVIDER", "local").lower()
        provider_class = self._providers.get(active_name)
        if not provider_class:
            raise ValueError(f"No storage provider found for name: {active_name}")
        return provider_class()


storage_registry = StorageRegistry()
