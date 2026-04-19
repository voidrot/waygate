from typing import Type, TypeVar

from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from waygate_core.plugin.hooks import PluginConfigRegistration, hookimpl
from waygate_core.plugin.llm import LLMProviderPlugin

PLUGIN_NAME = "OllamaProvider"

T = TypeVar("T", bound=BaseModel)


class OllamaProviderConfig(BaseModel):
    base_url: str = Field(default="http://localhost:11434")


class OllamaProvider(LLMProviderPlugin):
    plugin_name = PLUGIN_NAME

    def __init__(self, config: OllamaProviderConfig | None = None) -> None:
        self._config = config or OllamaProviderConfig()

    @staticmethod
    @hookimpl
    def waygate_llm_provider_plugin() -> type["OllamaProvider"]:
        return OllamaProvider

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        return PluginConfigRegistration(name=PLUGIN_NAME, config=OllamaProviderConfig)

    def get_llm(self, model_name: str, workflow_type: str | None = None) -> Runnable:
        raise NotImplementedError

    def get_structured_llm(
        self, schema: Type[T], model_name: str, workflow_type: str | None = None
    ) -> Runnable:
        raise NotImplementedError
