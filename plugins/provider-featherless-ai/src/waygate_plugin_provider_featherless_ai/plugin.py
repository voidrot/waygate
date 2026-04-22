"""Featherless AI-backed LLM provider for WayGate workflows."""

from typing import Any, Type, TypeVar

from langchain_core.embeddings import Embeddings
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel, Field, SecretStr, field_validator
from waygate_core.plugin.hooks import PluginConfigRegistration, hookimpl
from waygate_core.plugin.llm import (
    LLMConfigurationError,
    LLMInvocationRequest,
    LLMProviderCapabilities,
    LLMProviderPlugin,
    resolve_invocation_options,
)

from . import __VERSION__

PLUGIN_NAME = "FeatherlessAIProvider"

T = TypeVar("T", bound=BaseModel)


class FeatherlessAIProviderConfig(BaseModel):
    """Configuration for the Featherless AI provider."""

    featherless_api_key: SecretStr | None = Field(default=None)
    featherless_base_url: str = Field(default="https://api.featherless.ai/v1")

    @field_validator("featherless_base_url")
    @classmethod
    def _normalize_base_url(cls, value: str) -> str:
        """Normalize the API root URL expected by ChatOpenAI."""

        normalized = value.strip().rstrip("/")
        if not normalized:
            raise ValueError("featherless_base_url must not be empty")
        if normalized.endswith("/chat/completions"):
            raise ValueError(
                "featherless_base_url must point to the OpenAI-compatible API root, "
                "not the /chat/completions endpoint"
            )
        return normalized


class FeatherlessAIProvider(LLMProviderPlugin):
    """Provide ChatOpenAI runnables backed by Featherless AI."""

    plugin_name = PLUGIN_NAME

    def __init__(
        self,
        config: FeatherlessAIProviderConfig | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            config: Optional provider configuration.
        """

        self._config = config or FeatherlessAIProviderConfig()

    @property
    def name(self) -> str:
        """Return the canonical provider name."""

        return PLUGIN_NAME

    @property
    def description(self) -> str:
        """Return a short human-readable description."""

        return "LLM provider plugin for Featherless AI via ChatOpenAI"

    @property
    def version(self) -> str:
        """Return the provider version."""

        return __VERSION__

    @staticmethod
    @hookimpl
    def waygate_llm_provider_plugin() -> type["FeatherlessAIProvider"]:
        """Register the Featherless AI provider implementation."""

        return FeatherlessAIProvider

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        """Register the plugin configuration model."""

        return PluginConfigRegistration(
            name=PLUGIN_NAME,
            config=FeatherlessAIProviderConfig,
        )

    def get_capabilities(self) -> LLMProviderCapabilities:
        """Return provider capability metadata."""

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
                "presence_penalty",
                "frequency_penalty",
                "repetition_penalty",
                "min_p",
                "min_tokens",
                "stop_token_ids",
                "include_stop_str_in_output",
            },
        )

    def _build_chat_openai_kwargs(
        self,
        request: LLMInvocationRequest,
    ) -> dict[str, Any]:
        """Build ChatOpenAI keyword arguments from a workflow request."""

        resolved = resolve_invocation_options(request, self.get_capabilities())
        api_key = self._require_api_key()

        kwargs: dict[str, Any] = {
            "model": request.model_name,
            "api_key": api_key,
            "base_url": self._config.featherless_base_url,
        }
        extra_body: dict[str, Any] = {}

        for key, value in resolved.common_options.items():
            if key == "top_k":
                extra_body[key] = value
            else:
                kwargs[key] = value

        for key, value in resolved.provider_options.items():
            if key in {"presence_penalty", "frequency_penalty"}:
                kwargs[key] = value
            else:
                extra_body[key] = value

        if extra_body:
            kwargs["extra_body"] = extra_body

        return kwargs

    def _require_api_key(self) -> str:
        """Return the configured API key or raise a configuration error."""

        configured_key = self._config.featherless_api_key
        if configured_key is None:
            raise LLMConfigurationError(
                "FeatherlessAIProvider requires WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_API_KEY "
                "when it is the active LLM provider."
            )

        api_key = configured_key.get_secret_value().strip()
        if not api_key:
            raise LLMConfigurationError(
                "FeatherlessAIProvider requires WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_API_KEY "
                "when it is the active LLM provider."
            )
        return api_key

    def get_llm(self, request: LLMInvocationRequest) -> ChatOpenAI:
        """Return a configured ChatOpenAI runnable."""

        kwargs = self._build_chat_openai_kwargs(request)
        return ChatOpenAI(**kwargs)

    def validate_llm_readiness(self, request: LLMInvocationRequest) -> None:
        """Preflight a text-generation request for startup/readiness checks."""

        self.get_llm(request)

    def get_structured_llm(
        self,
        schema: Type[T],
        request: LLMInvocationRequest,
    ) -> Runnable:
        """Return a ChatOpenAI runnable with structured output enabled."""

        llm = self.get_llm(request)
        return llm.with_structured_output(schema)

    def validate_structured_llm_readiness(
        self,
        schema: type[BaseModel],
        request: LLMInvocationRequest,
    ) -> None:
        """Preflight a structured-output request for startup/readiness checks."""

        self.get_structured_llm(schema, request)

    def get_embeddings(self, model_name: str) -> Embeddings:
        """Return an embeddings client for the requested model."""

        return OpenAIEmbeddings(
            model=model_name,
            api_key=self._require_api_key(),
            base_url=self._config.featherless_base_url,
        )
