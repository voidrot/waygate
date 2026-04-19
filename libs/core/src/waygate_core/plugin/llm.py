from enum import StrEnum
from typing import Any, Type, TypeVar
from abc import ABC, abstractmethod
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class LLMOptionPolicy(StrEnum):
    STRICT = "strict"
    PERMISSIVE = "permissive"


class LLMCommonOptions(BaseModel):
    temperature: float | None = Field(default=None)
    top_p: float | None = Field(default=None)
    top_k: int | None = Field(default=None)
    max_tokens: int | None = Field(default=None)
    seed: int | None = Field(default=None)
    stop: list[str] | None = Field(default=None)


class LLMInvocationRequest(BaseModel):
    workflow_name: str
    model_name: str
    variables: dict[str, Any] = Field(default_factory=dict)
    common_options: LLMCommonOptions = Field(default_factory=LLMCommonOptions)
    provider_options: dict[str, dict[str, Any]] = Field(default_factory=dict)
    option_policy: LLMOptionPolicy = Field(default=LLMOptionPolicy.STRICT)


class LLMInvocationDiagnostics(BaseModel):
    dropped_common_options: list[str] = Field(default_factory=list)
    dropped_provider_options: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LLMResolvedOptions(BaseModel):
    common_options: dict[str, Any] = Field(default_factory=dict)
    provider_options: dict[str, Any] = Field(default_factory=dict)
    diagnostics: LLMInvocationDiagnostics = Field(
        default_factory=LLMInvocationDiagnostics
    )


class LLMProviderCapabilities(BaseModel):
    provider_name: str
    supports_structured_output: bool = Field(default=True)
    supported_common_options: set[str] = Field(default_factory=set)
    supported_provider_options: set[str] = Field(default_factory=set)


def resolve_invocation_options(
    request: LLMInvocationRequest,
    capabilities: LLMProviderCapabilities,
) -> LLMResolvedOptions:
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
        raise ValueError(
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
    """
    Abstract base for LLM provider plugins.

    LLM provider instances are cached process-wide at startup. Implement your
    provider as stateless where possible, or ensure thread-safe access to any
    mutable state.
    """

    plugin_group: str = "waygate.plugins.llm"
    hook_name: str = "waygate_llm_provider_plugin"

    @property
    def name(self) -> str:
        """
        The name of the plugin.

        Returns:
            str: The name of the plugin.
        """
        return self.__class__.__name__

    @property
    def description(self) -> str:
        """
        A brief description of the plugin.

        Returns:
            str: A description of the plugin.
        """
        return "No description provided."

    @property
    def version(self) -> str:
        """
        The version of the plugin.

        Returns:
            str: The version of the plugin.
        """
        return "0.0.0"

    @abstractmethod
    def get_capabilities(self) -> LLMProviderCapabilities:
        """Return provider capability metadata used for request validation."""
        raise NotImplementedError(
            "LLMProviderPlugin subclasses must implement get_capabilities"
        )

    @abstractmethod
    def get_llm(self, request: LLMInvocationRequest) -> Runnable:
        """
        Retrieve an LLM instance by name.

        Args:
            request (LLMInvocationRequest): Invocation context, variables, and options.

        Returns:
            An instance of the requested LLM model.
        """
        raise NotImplementedError("BaseLLMProvider subclasses must implement get_llm")

    @abstractmethod
    def get_structured_llm(
        self,
        schema: Type[T],
        request: LLMInvocationRequest,
    ) -> Runnable:
        """
        Retrieve a structured LLM instance that outputs data conforming to the provided schema.

        Args:
            schema (Type[T]): A Pydantic model class that defines the expected output structure.
            request (LLMInvocationRequest): Invocation context, variables, and options.

        Returns:
            StructuredLLM[T]: An instance of StructuredLLM that will output data conforming to the provided schema.
        """
        raise NotImplementedError(
            "BaseLLMProvider subclasses must implement get_structured_llm"
        )
