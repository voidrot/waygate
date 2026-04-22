"""Ollama-backed LLM provider for WayGate workflows."""

from typing import Any, Type, TypeVar

from langchain_core.embeddings import Embeddings
from langchain_core.runnables import Runnable
from langchain_ollama import ChatOllama, OllamaEmbeddings
from pydantic import BaseModel, Field, field_validator
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
    validate_model_on_init: bool = Field(default=True)

    @field_validator("base_url")
    @classmethod
    def _normalize_base_url(cls, value: str) -> str:
        """Normalize the Ollama host URL expected by the client."""

        normalized = value.strip().rstrip("/")
        if not normalized:
            raise ValueError("base_url must not be empty")
        if normalized.endswith("/api/chat") or normalized.endswith("/api/generate"):
            raise ValueError(
                "base_url must point to the Ollama server root, not a concrete /api endpoint"
            )
        return normalized


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
                "validate_model_on_init",
                "num_ctx",
                "num_gpu",
                "num_thread",
                "mirostat",
                "mirostat_tau",
                "mirostat_eta",
                "num_predict",
                "repeat_last_n",
                "repeat_penalty",
                "logprobs",
                "top_logprobs",
                "format",
                "reasoning",
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
            "validate_model_on_init": self._config.validate_model_on_init,
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

    def validate_llm_readiness(self, request: LLMInvocationRequest) -> None:
        """Preflight a text-generation request for startup/readiness checks."""

        self.get_llm(request)

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
        return llm.with_structured_output(
            schema,
            method="json_schema",
            include_raw=True,
        )

    def validate_structured_llm_readiness(
        self,
        schema: type[BaseModel],
        request: LLMInvocationRequest,
    ) -> None:
        """Preflight a structured-output request for startup/readiness checks."""

        self.get_structured_llm(schema, request)

    def get_embeddings(self, model_name: str) -> Embeddings:
        """Return an Ollama embeddings client for the requested model."""

        return OllamaEmbeddings(
            model=model_name,
            base_url=self._config.base_url,
        )
