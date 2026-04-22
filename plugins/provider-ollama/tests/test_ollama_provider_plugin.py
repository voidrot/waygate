from pydantic import BaseModel, ValidationError
import pytest

from waygate_core.plugin.llm import (
    LLMCommonOptions,
    LLMConfigurationError,
    LLMInvocationRequest,
    LLMOptionPolicy,
)
from waygate_plugin_provider_ollama.plugin import (
    OllamaProvider,
    OllamaProviderConfig,
)


class _DraftSchema(BaseModel):
    summary: str


def _install_fake_langchain_ollama(monkeypatch, created):
    class FakeChatOllama:
        def __init__(self, model: str, **kwargs) -> None:
            created.append((model, kwargs))

        def with_structured_output(self, schema):
            return {"schema": schema.__name__, "model": created[-1][0]}

    from waygate_plugin_provider_ollama import plugin as plugin_module

    monkeypatch.setattr(plugin_module, "ChatOllama", FakeChatOllama)


def _install_fake_ollama_embeddings(monkeypatch, created):
    class FakeOllamaEmbeddings:
        def __init__(self, model: str, **kwargs) -> None:
            created.append((model, kwargs))

    from waygate_plugin_provider_ollama import plugin as plugin_module

    monkeypatch.setattr(plugin_module, "OllamaEmbeddings", FakeOllamaEmbeddings)


def test_get_llm_maps_common_and_provider_options(monkeypatch) -> None:
    created: list[tuple[str, dict]] = []
    _install_fake_langchain_ollama(monkeypatch, created)

    provider = OllamaProvider(
        config=OllamaProviderConfig(base_url="http://ollama.local")
    )
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="qwen3.5:9b",
        common_options=LLMCommonOptions(temperature=0.3, max_tokens=256),
        provider_options={"OllamaProvider": {"num_ctx": 4096}},
        option_policy=LLMOptionPolicy.STRICT,
    )

    provider.get_llm(request)

    assert created == [
        (
            "qwen3.5:9b",
            {
                "base_url": "http://ollama.local",
                "validate_model_on_init": True,
                "temperature": 0.3,
                "num_ctx": 4096,
                "num_predict": 256,
            },
        )
    ]


def test_get_structured_llm_returns_structured_model(monkeypatch) -> None:
    created: list[tuple[str, dict]] = []
    _install_fake_langchain_ollama(monkeypatch, created)

    provider = OllamaProvider()
    request = LLMInvocationRequest(
        workflow_name="review",
        model_name="qwen3.5:9b",
        common_options=LLMCommonOptions(temperature=0.0),
    )

    structured = provider.get_structured_llm(_DraftSchema, request)

    assert structured == {"schema": "_DraftSchema", "model": "qwen3.5:9b"}


def test_validate_llm_readiness_constructs_client(monkeypatch) -> None:
    created: list[tuple[str, dict]] = []
    _install_fake_langchain_ollama(monkeypatch, created)

    provider = OllamaProvider(
        config=OllamaProviderConfig(base_url="http://ollama.local")
    )
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="qwen3.5:9b",
    )

    provider.validate_llm_readiness(request)

    assert created == [
        (
            "qwen3.5:9b",
            {
                "base_url": "http://ollama.local",
                "validate_model_on_init": True,
            },
        )
    ]


def test_explicit_num_predict_takes_precedence_over_max_tokens(monkeypatch) -> None:
    created: list[tuple[str, dict]] = []
    _install_fake_langchain_ollama(monkeypatch, created)

    provider = OllamaProvider(
        config=OllamaProviderConfig(base_url="http://ollama.local")
    )
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="qwen3.5:9b",
        common_options=LLMCommonOptions(max_tokens=256),
        provider_options={"OllamaProvider": {"num_predict": 128}},
        option_policy=LLMOptionPolicy.STRICT,
    )

    provider.get_llm(request)

    assert created == [
        (
            "qwen3.5:9b",
            {
                "base_url": "http://ollama.local",
                "validate_model_on_init": True,
                "num_predict": 128,
            },
        )
    ]


def test_strict_option_policy_rejects_unsupported_options(monkeypatch) -> None:
    created: list[tuple[str, dict]] = []
    _install_fake_langchain_ollama(monkeypatch, created)

    provider = OllamaProvider()
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="qwen3.5:9b",
        common_options=LLMCommonOptions(temperature=0.1),
        provider_options={"OllamaProvider": {"bad_option": True}},
        option_policy=LLMOptionPolicy.STRICT,
    )

    with pytest.raises(LLMConfigurationError, match="Unsupported LLM options"):
        provider.get_llm(request)

    assert created == []


def test_permissive_option_policy_drops_unsupported_options(monkeypatch) -> None:
    created: list[tuple[str, dict]] = []
    _install_fake_langchain_ollama(monkeypatch, created)

    provider = OllamaProvider()
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="qwen3.5:9b",
        common_options=LLMCommonOptions(temperature=0.1),
        provider_options={
            "OllamaProvider": {
                "num_ctx": 4096,
                "bad_option": True,
            }
        },
        option_policy=LLMOptionPolicy.PERMISSIVE,
    )

    provider.get_llm(request)

    assert created == [
        (
            "qwen3.5:9b",
            {
                "base_url": "http://localhost:11434",
                "validate_model_on_init": True,
                "temperature": 0.1,
                "num_ctx": 4096,
            },
        )
    ]


def test_base_url_normalizes_trailing_slash() -> None:
    config = OllamaProviderConfig(base_url="http://ollama.local/")

    assert config.base_url == "http://ollama.local"


def test_base_url_rejects_api_endpoints() -> None:
    with pytest.raises(ValidationError, match="Ollama server root"):
        OllamaProviderConfig(base_url="http://ollama.local/api/chat")

    with pytest.raises(ValidationError, match="Ollama server root"):
        OllamaProviderConfig(base_url="http://ollama.local/api/generate")


def test_validate_model_on_init_from_config_is_forwarded(monkeypatch) -> None:
    created: list[tuple[str, dict]] = []
    _install_fake_langchain_ollama(monkeypatch, created)

    provider = OllamaProvider(
        config=OllamaProviderConfig(
            base_url="http://ollama.local",
            validate_model_on_init=True,
        )
    )
    request = LLMInvocationRequest(
        workflow_name="draft",
        model_name="qwen3.5:9b",
    )

    provider.get_llm(request)

    assert created == [
        (
            "qwen3.5:9b",
            {
                "base_url": "http://ollama.local",
                "validate_model_on_init": True,
            },
        )
    ]


def test_get_embeddings_builds_ollama_embeddings_client(monkeypatch) -> None:
    created: list[tuple[str, dict]] = []
    _install_fake_ollama_embeddings(monkeypatch, created)

    provider = OllamaProvider(
        config=OllamaProviderConfig(base_url="http://ollama.local/")
    )

    provider.get_embeddings("nomic-embed-text")

    assert created == [
        (
            "nomic-embed-text",
            {
                "base_url": "http://ollama.local",
            },
        )
    ]
