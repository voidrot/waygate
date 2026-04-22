from pydantic import BaseModel, SecretStr, ValidationError
import pytest

from waygate_core.plugin.llm import (
    LLMCommonOptions,
    LLMConfigurationError,
    LLMInvocationRequest,
    LLMOptionPolicy,
)
from waygate_plugin_provider_featherless_ai.plugin import (
    FeatherlessAIProvider,
    FeatherlessAIProviderConfig,
)


class _DraftSchema(BaseModel):
    summary: str


def _install_fake_langchain_openai(monkeypatch, created):
    class FakeChatOpenAI:
        def __init__(self, **kwargs) -> None:
            created.append(kwargs)

        def with_structured_output(self, schema):
            return {"schema": schema.__name__, "model": created[-1]["model"]}

    from waygate_plugin_provider_featherless_ai import plugin as plugin_module

    monkeypatch.setattr(plugin_module, "ChatOpenAI", FakeChatOpenAI)


def _install_fake_openai_embeddings(monkeypatch, created):
    class FakeOpenAIEmbeddings:
        def __init__(self, **kwargs) -> None:
            created.append(kwargs)

    from waygate_plugin_provider_featherless_ai import plugin as plugin_module

    monkeypatch.setattr(plugin_module, "OpenAIEmbeddings", FakeOpenAIEmbeddings)


def test_get_llm_maps_common_and_provider_options(monkeypatch) -> None:
    created: list[dict] = []
    _install_fake_langchain_openai(monkeypatch, created)

    provider = FeatherlessAIProvider(
        config=FeatherlessAIProviderConfig(
            featherless_api_key=SecretStr("test-key"),
            featherless_base_url="https://featherless.invalid/v1",
        )
    )
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="Qwen/Qwen3-32B",
        common_options=LLMCommonOptions(
            temperature=0.3,
            top_k=40,
            top_p=0.8,
            max_tokens=256,
            seed=99,
            stop=["END"],
        ),
        provider_options={
            "FeatherlessAIProvider": {
                "presence_penalty": 0.1,
                "frequency_penalty": 0.2,
                "repetition_penalty": 1.05,
                "min_p": 0.05,
                "min_tokens": 32,
                "stop_token_ids": [42, 43],
                "include_stop_str_in_output": True,
            }
        },
        option_policy=LLMOptionPolicy.STRICT,
    )

    provider.get_llm(request)

    assert created == [
        {
            "model": "Qwen/Qwen3-32B",
            "api_key": "test-key",
            "base_url": "https://featherless.invalid/v1",
            "temperature": 0.3,
            "top_p": 0.8,
            "max_tokens": 256,
            "seed": 99,
            "stop": ["END"],
            "presence_penalty": 0.1,
            "frequency_penalty": 0.2,
            "extra_body": {
                "top_k": 40,
                "repetition_penalty": 1.05,
                "min_p": 0.05,
                "min_tokens": 32,
                "stop_token_ids": [42, 43],
                "include_stop_str_in_output": True,
            },
        }
    ]


def test_get_structured_llm_returns_structured_model(monkeypatch) -> None:
    created: list[dict] = []
    _install_fake_langchain_openai(monkeypatch, created)

    provider = FeatherlessAIProvider(
        config=FeatherlessAIProviderConfig(
            featherless_api_key=SecretStr("test-key"),
        )
    )
    request = LLMInvocationRequest(
        workflow_name="review",
        model_name="meta-llama/Meta-Llama-3.1-8B-Instruct",
        common_options=LLMCommonOptions(temperature=0.0),
    )

    structured = provider.get_structured_llm(_DraftSchema, request)

    assert structured == {
        "schema": "_DraftSchema",
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
    }


def test_validate_llm_readiness_constructs_client(monkeypatch) -> None:
    created: list[dict] = []
    _install_fake_langchain_openai(monkeypatch, created)

    provider = FeatherlessAIProvider(
        config=FeatherlessAIProviderConfig(
            featherless_api_key=SecretStr("test-key"),
            featherless_base_url="https://featherless.invalid/v1",
        )
    )
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="Qwen/Qwen3-32B",
    )

    provider.validate_llm_readiness(request)

    assert created == [
        {
            "model": "Qwen/Qwen3-32B",
            "api_key": "test-key",
            "base_url": "https://featherless.invalid/v1",
        }
    ]


def test_get_llm_requires_api_key_when_provider_is_used(monkeypatch) -> None:
    created: list[dict] = []
    _install_fake_langchain_openai(monkeypatch, created)

    provider = FeatherlessAIProvider()
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="Qwen/Qwen3-32B",
        common_options=LLMCommonOptions(temperature=0.1),
    )

    with pytest.raises(
        LLMConfigurationError,
        match="WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_API_KEY",
    ):
        provider.get_llm(request)

    assert created == []


def test_blank_api_key_is_rejected_before_client_construction(monkeypatch) -> None:
    created: list[dict] = []
    _install_fake_langchain_openai(monkeypatch, created)

    provider = FeatherlessAIProvider(
        config=FeatherlessAIProviderConfig(
            featherless_api_key=SecretStr("   "),
        )
    )
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="Qwen/Qwen3-32B",
    )

    with pytest.raises(
        LLMConfigurationError,
        match="WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_API_KEY",
    ):
        provider.get_llm(request)

    assert created == []


def test_strict_option_policy_rejects_unsupported_options(monkeypatch) -> None:
    created: list[dict] = []
    _install_fake_langchain_openai(monkeypatch, created)

    provider = FeatherlessAIProvider(
        config=FeatherlessAIProviderConfig(
            featherless_api_key=SecretStr("test-key"),
        )
    )
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="Qwen/Qwen3-32B",
        common_options=LLMCommonOptions(temperature=0.3, top_k=40),
        provider_options={
            "FeatherlessAIProvider": {
                "presence_penalty": 0.1,
                "bad_provider_option": True,
            }
        },
        option_policy=LLMOptionPolicy.STRICT,
    )

    with pytest.raises(LLMConfigurationError, match="Unsupported LLM options"):
        provider.get_llm(request)

    assert created == []


def test_permissive_option_policy_drops_unsupported_options(monkeypatch) -> None:
    created: list[dict] = []
    _install_fake_langchain_openai(monkeypatch, created)

    provider = FeatherlessAIProvider(
        config=FeatherlessAIProviderConfig(
            featherless_api_key=SecretStr("test-key"),
        )
    )
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="Qwen/Qwen3-32B",
        common_options=LLMCommonOptions(temperature=0.3, top_k=40),
        provider_options={
            "FeatherlessAIProvider": {
                "presence_penalty": 0.1,
                "bad_provider_option": True,
            }
        },
        option_policy=LLMOptionPolicy.PERMISSIVE,
    )

    provider.get_llm(request)

    assert created == [
        {
            "model": "Qwen/Qwen3-32B",
            "api_key": "test-key",
            "base_url": "https://api.featherless.ai/v1",
            "temperature": 0.3,
            "presence_penalty": 0.1,
            "extra_body": {"top_k": 40},
        }
    ]


def test_base_url_normalizes_trailing_slash() -> None:
    config = FeatherlessAIProviderConfig(
        featherless_api_key=SecretStr("test-key"),
        featherless_base_url="https://featherless.invalid/v1/",
    )

    assert config.featherless_base_url == "https://featherless.invalid/v1"


def test_base_url_rejects_chat_completions_endpoint() -> None:
    with pytest.raises(ValidationError, match="OpenAI-compatible API root"):
        FeatherlessAIProviderConfig(
            featherless_api_key=SecretStr("test-key"),
            featherless_base_url="https://featherless.invalid/v1/chat/completions",
        )


def test_get_embeddings_builds_openai_embeddings_client(monkeypatch) -> None:
    created: list[dict] = []
    _install_fake_openai_embeddings(monkeypatch, created)

    provider = FeatherlessAIProvider(
        config=FeatherlessAIProviderConfig(
            featherless_api_key=SecretStr("test-key"),
            featherless_base_url="https://featherless.invalid/v1/",
        )
    )

    provider.get_embeddings("text-embedding-3-large")

    assert created == [
        {
            "model": "text-embedding-3-large",
            "api_key": "test-key",
            "base_url": "https://featherless.invalid/v1",
        }
    ]
