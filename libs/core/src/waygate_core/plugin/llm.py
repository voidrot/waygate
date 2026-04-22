"""LLM provider contracts and request-option resolution helpers."""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Protocol, Type, TypeVar, runtime_checkable

from langchain_core.embeddings import Embeddings
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class LLMConfigurationError(ValueError):
    """Raised when LLM configuration cannot be satisfied by the active provider."""


class LLMOptionPolicy(StrEnum):
    STRICT = "strict"
    PERMISSIVE = "permissive"


class LLMCommonOptions(BaseModel):
    """Common provider-agnostic LLM options shared across workflows."""

    temperature: float | None = Field(default=None)
    top_p: float | None = Field(default=None)
    top_k: int | None = Field(default=None)
    max_tokens: int | None = Field(default=None)
    seed: int | None = Field(default=None)
    stop: list[str] | None = Field(default=None)


class LLMInvocationRequest(BaseModel):
    """Request context used to resolve a provider model invocation."""

    workflow_name: str
    target_name: str | None = Field(default=None)
    model_name: str
    variables: dict[str, Any] = Field(default_factory=dict)
    common_options: LLMCommonOptions = Field(default_factory=LLMCommonOptions)
    provider_options: dict[str, dict[str, Any]] = Field(default_factory=dict)
    option_policy: LLMOptionPolicy = Field(default=LLMOptionPolicy.STRICT)


class LLMInvocationDiagnostics(BaseModel):
    """Warnings and dropped-option details returned by option resolution."""

    dropped_common_options: list[str] = Field(default_factory=list)
    dropped_provider_options: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LLMResolvedOptions(BaseModel):
    """Normalized option payload passed to provider implementations."""

    common_options: dict[str, Any] = Field(default_factory=dict)
    provider_options: dict[str, Any] = Field(default_factory=dict)
    diagnostics: LLMInvocationDiagnostics = Field(
        default_factory=LLMInvocationDiagnostics
    )


class LLMProviderCapabilities(BaseModel):
    """Advertises which option names a provider accepts."""

    provider_name: str
    supports_structured_output: bool = Field(default=True)
    supported_common_options: set[str] = Field(default_factory=set)
    supported_provider_options: set[str] = Field(default_factory=set)


@runtime_checkable
class LLMReadinessProbe(Protocol):
    """Optional companion protocol for provider-specific readiness checks."""

    def validate_llm_readiness(self, request: LLMInvocationRequest) -> None:
        """Preflight a text-generation request without invoking the model."""

    def validate_structured_llm_readiness(
        self,
        schema: type[BaseModel],
        request: LLMInvocationRequest,
    ) -> None:
        """Preflight a structured-output request without invoking the model."""


@runtime_checkable
class LLMEmbeddingsProvider(Protocol):
    """Optional companion protocol for embedding-capable LLM providers."""

    def get_embeddings(self, model_name: str) -> Embeddings:
        """Return an embeddings client for the requested model name."""


def resolve_invocation_options(
    request: LLMInvocationRequest,
    capabilities: LLMProviderCapabilities,
) -> LLMResolvedOptions:
    """Filter request options to the subset supported by a provider.

    Strict mode fails fast on unsupported options. Permissive mode drops them
    and records diagnostics so callers can surface the mismatch.

    Args:
        request: The invocation request to normalize.
        capabilities: The provider capability metadata.

    Returns:
        The resolved option payload and diagnostics.

    Raises:
        LLMConfigurationError: If strict mode encounters unsupported options.
    """

    common_options = request.common_options.model_dump(exclude_none=True)
    provider_scoped_options = request.provider_options.get(
        capabilities.provider_name, {}
    )
    diagnostics = LLMInvocationDiagnostics()

    supported_common = capabilities.supported_common_options
    supported_provider = capabilities.supported_provider_options

    unknown_common = [key for key in common_options if key not in supported_common]
    unknown_provider = [
        key for key in provider_scoped_options if key not in supported_provider
    ]

    if request.option_policy is LLMOptionPolicy.STRICT and (
        unknown_common or unknown_provider
    ):
        raise LLMConfigurationError(
            "Unsupported LLM options for provider "
            f"{capabilities.provider_name}: "
            f"common={unknown_common}, provider={unknown_provider}"
        )

    if unknown_common:
        diagnostics.dropped_common_options.extend(sorted(unknown_common))
        diagnostics.warnings.append(
            f"Dropped unsupported common options: {sorted(unknown_common)}"
        )
    if unknown_provider:
        diagnostics.dropped_provider_options.extend(sorted(unknown_provider))
        diagnostics.warnings.append(
            f"Dropped unsupported provider options: {sorted(unknown_provider)}"
        )

    filtered_common = {
        key: value for key, value in common_options.items() if key in supported_common
    }
    filtered_provider = {
        key: value
        for key, value in provider_scoped_options.items()
        if key in supported_provider
    }

    return LLMResolvedOptions(
        common_options=filtered_common,
        provider_options=filtered_provider,
        diagnostics=diagnostics,
    )


class LLMProviderPlugin(ABC):
    """Abstract base for LLM provider plugins.

    LLM provider instances are cached process-wide at startup. Implement your
    provider as stateless where possible, or ensure thread-safe access to any
    mutable state.
    """

    plugin_group: str = "waygate.plugins.llm"
    hook_name: str = "waygate_llm_provider_plugin"

    @property
    def name(self) -> str:
        """Return the plugin name.

        Returns:
            The plugin name.
        """
        return self.__class__.__name__

    @property
    def description(self) -> str:
        """Return a brief plugin description.

        Returns:
            The plugin description.
        """
        return "No description provided."

    @property
    def version(self) -> str:
        """Return the plugin version.

        Returns:
            The plugin version.
        """
        return "0.0.0"

    @abstractmethod
    def get_capabilities(self) -> LLMProviderCapabilities:
        """Return provider capability metadata.

        Returns:
            The provider capability metadata used for request validation.
        """
        raise NotImplementedError(
            "LLMProviderPlugin subclasses must implement get_capabilities"
        )

    @abstractmethod
    def get_llm(self, request: LLMInvocationRequest) -> Runnable:
        """Retrieve an LLM instance for the given request.

        Args:
            request: The invocation context, variables, and options.

        Returns:
            A runnable for the requested model.
        """
        raise NotImplementedError("BaseLLMProvider subclasses must implement get_llm")

    @abstractmethod
    def get_structured_llm(
        self,
        schema: Type[T],
        request: LLMInvocationRequest,
    ) -> Runnable:
        """Retrieve a structured LLM instance.

        Args:
            schema: The Pydantic model class describing the output structure.
            request: The invocation context, variables, and options.

        Returns:
            A runnable that produces output conforming to ``schema``.
        """
        raise NotImplementedError(
            "BaseLLMProvider subclasses must implement get_structured_llm"
        )
