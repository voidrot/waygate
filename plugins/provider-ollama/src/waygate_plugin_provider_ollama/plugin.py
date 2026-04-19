from typing import Type, TypeVar, Any

from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from waygate_core.plugin.hooks import PluginConfigRegistration, hookimpl
from waygate_core.plugin.llm import (
    LLMInvocationRequest,
    LLMProviderCapabilities,
    LLMProviderPlugin,
    resolve_invocation_options,
)

from . import __VERSION__

PLUGIN_NAME = "OllamaProvider"

T = TypeVar("T", bound=BaseModel)


class OllamaProviderConfig(BaseModel):
    base_url: str = Field(default="http://localhost:11434")


class OllamaProvider(LLMProviderPlugin):
    def __init__(self, config: OllamaProviderConfig | None = None) -> None:
        self._config = config or OllamaProviderConfig()

    @property
    def name(self) -> str:
        return PLUGIN_NAME

    @property
    def description(self) -> str:
        return "LLM provider plugin for Ollama"

    @property
    def version(self) -> str:
        return __VERSION__

    @staticmethod
    @hookimpl
    def waygate_llm_provider_plugin() -> type["OllamaProvider"]:
        return OllamaProvider

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        return PluginConfigRegistration(name=PLUGIN_NAME, config=OllamaProviderConfig)

    def get_capabilities(self) -> LLMProviderCapabilities:
        return LLMProviderCapabilities(
            provider_name=PLUGIN_NAME,
            supports_structured_output=True,
            supported_common_options={
                "temperature",
                "top_k",
                "top_p",
                "seed",
                "stop",
                "max_tokens",
            },
            supported_provider_options={
                "num_ctx",
                "mirostat",
                "mirostat_tau",
                "mirostat_eta",
                "num_predict",
                "repeat_last_n",
                "repeat_penalty",
                "tfs_z",
                "keep_alive",
            },
        )

    def _build_ollama_kwargs(self, request: LLMInvocationRequest) -> dict[str, Any]:
        resolved = resolve_invocation_options(request, self.get_capabilities())

        kwargs: dict[str, Any] = {
            "base_url": self._config.base_url,
            **resolved.common_options,
            **resolved.provider_options,
        }

        if "max_tokens" in kwargs and "num_predict" not in kwargs:
            kwargs["num_predict"] = kwargs.pop("max_tokens")
        else:
            kwargs.pop("max_tokens", None)

        return kwargs

    def get_llm(self, request: LLMInvocationRequest) -> ChatOllama:
        kwargs = self._build_ollama_kwargs(request)
        return ChatOllama(model=request.model_name, **kwargs)

    def get_structured_llm(
        self,
        schema: Type[T],
        request: LLMInvocationRequest,
    ) -> Runnable:
        llm = self.get_llm(request)
        return llm.with_structured_output(schema)
