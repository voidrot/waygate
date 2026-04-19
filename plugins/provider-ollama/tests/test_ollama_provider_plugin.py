from pydantic import BaseModel

from waygate_core.plugin.llm import (
    LLMCommonOptions,
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
