# libs/core/llm_registry.py
import importlib.metadata
from typing import Dict
from waygate_core.llm_base import LLMProviderPlugin
import logging

logger = logging.getLogger(__name__)


class LLMRegistry:
    def __init__(self):
        self._providers: Dict[str, type[LLMProviderPlugin]] = {}

    def discover_providers(self):
        entry_points = importlib.metadata.entry_points(group="waygate.plugins.llm")
        for ep in entry_points:
            try:
                provider_class = ep.load()
                temp_instance = provider_class()
                self._providers[temp_instance.provider_name] = provider_class
                logger.info("Discovered LLM provider: %s", temp_instance.provider_name)
            except Exception as e:
                logger.exception("Failed to load LLM provider %s: %s", ep.name, e)

    def get_provider(self, provider: str) -> LLMProviderPlugin:

        provider_class = self._providers.get(provider.lower())

        if not provider_class:
            raise ValueError(
                f"LLM provider '{provider}' not found. "
                f"Available: {list(self._providers.keys())}"
            )
        return provider_class()


llm_registry = LLMRegistry()
