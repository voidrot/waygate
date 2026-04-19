import pytest

from waygate_core.plugin.llm import (
    LLMCommonOptions,
    LLMConfigurationError,
    LLMInvocationRequest,
    LLMOptionPolicy,
    LLMProviderCapabilities,
    resolve_invocation_options,
)


def _capabilities() -> LLMProviderCapabilities:
    return LLMProviderCapabilities(
        provider_name="OllamaProvider",
        supported_common_options={"temperature", "top_p", "max_tokens"},
        supported_provider_options={"num_ctx", "num_predict"},
    )


def test_resolve_options_strict_rejects_unknown_options() -> None:
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="qwen3.5:9b",
        common_options=LLMCommonOptions(temperature=0.1, top_k=10),
        provider_options={"OllamaProvider": {"num_ctx": 4096, "bad_option": 1}},
        option_policy=LLMOptionPolicy.STRICT,
    )

    with pytest.raises(LLMConfigurationError, match="Unsupported LLM options"):
        resolve_invocation_options(request, _capabilities())


def test_resolve_options_permissive_drops_unsupported_options() -> None:
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="qwen3.5:9b",
        common_options=LLMCommonOptions(temperature=0.1, top_k=10),
        provider_options={"OllamaProvider": {"num_ctx": 4096, "bad_option": 1}},
        option_policy=LLMOptionPolicy.PERMISSIVE,
    )

    resolved = resolve_invocation_options(request, _capabilities())

    assert resolved.common_options == {"temperature": 0.1}
    assert resolved.provider_options == {"num_ctx": 4096}
    assert resolved.diagnostics.dropped_common_options == ["top_k"]
    assert resolved.diagnostics.dropped_provider_options == ["bad_option"]
