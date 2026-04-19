"""Ollama-backed LLM provider for WayGate workflows."""

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
    """Configuration for the Ollama provider."""

    base_url: str = Field(default="http://localhost:11434")


class OllamaProvider(LLMProviderPlugin):
    """Provide LLM and structured LLM runnables from Ollama."""

    plugin_name = PLUGIN_NAME

    def __init__(self, config: OllamaProviderConfig | None = None) -> None:
        """Initialize the Ollama provider.

        Args:
            config: Optional provider configuration.
        """

        self._config = config or OllamaProviderConfig()

    @property
    def name(self) -> str:
        """Return the canonical provider name.

        Returns:
            The plugin name used for registration and lookups.
        """

        return PLUGIN_NAME

    @property
    def description(self) -> str:
        """Return a short human-readable description.

        Returns:
            A description of the provider.
        """

        return "LLM provider plugin for Ollama"

    @property
    def version(self) -> str:
        """Return the provider version.

        Returns:
            The package version string.
        """

        return __VERSION__

    @staticmethod
    @hookimpl
    def waygate_llm_provider_plugin() -> type["OllamaProvider"]:
        """Register the Ollama provider implementation.

        Returns:
            The plugin class to register with Pluggy.
        """

        return OllamaProvider

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        """Register the plugin configuration model.

        Returns:
            The plugin config registration metadata.
        """

        return PluginConfigRegistration(name=PLUGIN_NAME, config=OllamaProviderConfig)

    def get_capabilities(self) -> LLMProviderCapabilities:
        """Return the provider capabilities advertised to the workflow layer."""

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
        """Build Ollama keyword arguments from a workflow request.

        Args:
            request: The invocation request.

        Returns:
            The keyword arguments to pass to ChatOllama.
        """

        resolved = resolve_invocation_options(request, self.get_capabilities())

        kwargs: dict[str, Any] = {
            "base_url": self._config.base_url,
            **resolved.common_options,
            **resolved.provider_options,
        }

        if "max_tokens" in kwargs and "num_predict" not in kwargs:
            # Ollama expects num_predict rather than the generic max_tokens name.
            kwargs["num_predict"] = kwargs.pop("max_tokens")
        else:
            kwargs.pop("max_tokens", None)

        return kwargs

    def get_llm(self, request: LLMInvocationRequest) -> ChatOllama:
        """Return a configured ChatOllama runnable.

        Args:
            request: The invocation request.

        Returns:
            A ChatOllama runnable configured for the requested model.
        """

        kwargs = self._build_ollama_kwargs(request)
        return ChatOllama(model=request.model_name, **kwargs)

    def get_structured_llm(
        self,
        schema: Type[T],
        request: LLMInvocationRequest,
    ) -> Runnable:
        """Return a ChatOllama runnable with structured output enabled.

        Args:
            schema: The schema to validate against.
            request: The invocation request.

        Returns:
            A runnable that emits structured output matching ``schema``.
        """

        llm = self.get_llm(request)
        return llm.with_structured_output(schema)
