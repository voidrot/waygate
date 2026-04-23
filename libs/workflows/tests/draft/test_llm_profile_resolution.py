from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from waygate_core.plugin import LLMOptionPolicy
from waygate_core.plugin import LLMConfigurationError
from waygate_core.plugin import LLMProviderCapabilities
from waygate_workflows.agents.review import review_draft_with_specialist
from waygate_workflows.runtime.llm import resolve_chat_model
from waygate_workflows.agents.synthesis import synthesize_draft_with_specialist
from waygate_workflows.runtime.llm import build_llm_request
from waygate_workflows.runtime.llm import invoke_text_stage
from waygate_workflows.runtime.llm import invoke_structured_stage
from waygate_workflows.runtime.llm import recover_structured_result
from waygate_workflows.runtime.llm import resolve_embeddings_model
from waygate_workflows.runtime.llm import validate_compile_llm_readiness
from waygate_workflows.schema import DocumentAnalysisResultModel
from waygate_plugin_provider_featherless_ai.plugin import (
    FeatherlessAIProvider,
    FeatherlessAIProviderConfig,
)
from waygate_plugin_provider_ollama.plugin import OllamaProvider, OllamaProviderConfig


class _FakeCoreSettings:
    def __init__(self, llm_workflow_profiles: dict[str, object]) -> None:
        self.llm_workflow_profiles = llm_workflow_profiles
        self.llm_plugin_name = "OllamaProvider"


class _StructuredResult(BaseModel):
    summary: str


def test_build_llm_request_prefers_target_profile_and_inherits_compile_defaults(
    monkeypatch,
) -> None:
    from waygate_core.config.schema import LLMWorkflowProfile

    core_settings = _FakeCoreSettings(
        {
            "draft": LLMWorkflowProfile(
                common_options={"top_p": 0.9},
                provider_options={"OllamaProvider": {"num_predict": 512}},
            ),
            "compile": LLMWorkflowProfile(
                common_options={"temperature": 0.1},
                provider_options={"OllamaProvider": {"num_ctx": 8192}},
                option_policy=LLMOptionPolicy.PERMISSIVE,
            ),
            "compile.synthesis": LLMWorkflowProfile(
                model_name="role-model",
                provider_options={"OllamaProvider": {"num_predict": 1200}},
            ),
        }
    )

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.resolve_llm_provider",
        lambda: (object(), core_settings),
    )

    request = build_llm_request(
        "compile",
        "fallback-model",
        target_name="compile.synthesis",
    )

    assert request.workflow_name == "compile"
    assert request.target_name == "compile.synthesis"
    assert request.model_name == "role-model"
    assert request.common_options.temperature == 0.1
    assert request.common_options.top_p == 0.9
    assert request.provider_options == {
        "OllamaProvider": {
            "num_ctx": 8192,
            "num_predict": 1200,
        }
    }
    assert request.option_policy is LLMOptionPolicy.PERMISSIVE


def test_build_llm_request_falls_back_to_legacy_stage_profile(monkeypatch) -> None:
    from waygate_core.config.schema import LLMWorkflowProfile

    core_settings = _FakeCoreSettings(
        {
            "draft": LLMWorkflowProfile(
                model_name="legacy-draft-model",
                common_options={"temperature": 0.3},
                option_policy=LLMOptionPolicy.PERMISSIVE,
            )
        }
    )

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.resolve_llm_provider",
        lambda: (object(), core_settings),
    )

    request = build_llm_request(
        "compile",
        "fallback-model",
        target_name="compile.source-analysis.summary",
    )

    assert request.model_name == "legacy-draft-model"
    assert request.common_options.temperature == 0.3
    assert request.option_policy is LLMOptionPolicy.PERMISSIVE


def test_synthesis_and_review_use_compile_target_ids(monkeypatch) -> None:
    resolved_models: list[tuple[str, str, str | None]] = []

    def fake_invoke_structured_stage(
        *,
        schema,
        workflow_name: str,
        fallback_model_name: str,
        target_name: str | None = None,
        system_prompt: str,
        user_prompt: str,
    ) -> object:
        resolved_models.append((workflow_name, fallback_model_name, target_name))
        return schema.model_validate({"approved": True, "feedback": []})

    class FakeMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class FakeSynthesisAgent:
        def invoke(self, payload: dict[str, object]) -> dict[str, object]:
            return {"messages": [FakeMessage("# Draft")]}

    create_agent_results = iter([FakeSynthesisAgent()])

    monkeypatch.setattr(
        "waygate_workflows.agents.synthesis.resolve_chat_model",
        lambda workflow_name, fallback_model_name, *, target_name=None, requires_structured_output=False: (
            resolved_models.append((workflow_name, fallback_model_name, target_name))
            or object()
        ),
    )
    monkeypatch.setattr(
        "waygate_workflows.agents.synthesis.create_agent",
        lambda **kwargs: next(create_agent_results),
    )
    monkeypatch.setattr(
        "waygate_workflows.agents.review.invoke_structured_stage",
        fake_invoke_structured_stage,
    )

    state = {
        "source_set_key": "set-key",
        "document_summaries": [],
        "extracted_metadata": [],
        "canonical_topics": [],
        "canonical_tags": [],
        "glossary": [],
        "entity_registry": [],
        "claim_ledger": [],
        "current_draft": "# Draft",
        "source_documents": [],
    }

    assert (
        synthesize_draft_with_specialist(state, draft_model_name="draft-model")
        == "# Draft"
    )
    review_result = review_draft_with_specialist(
        state,
        review_model_name="review-model",
    )

    assert review_result.approved is True
    assert resolved_models == [
        ("compile", "draft-model", "compile.synthesis"),
        ("compile", "review-model", "compile.review"),
    ]


def test_resolve_chat_model_rejects_unsupported_strict_options(monkeypatch) -> None:
    from waygate_core.config.schema import LLMWorkflowProfile

    class FakeProvider:
        def __init__(self) -> None:
            self.called = False

        def get_capabilities(self) -> LLMProviderCapabilities:
            return LLMProviderCapabilities(
                provider_name="OllamaProvider",
                supports_structured_output=True,
                supported_common_options={"temperature"},
                supported_provider_options={"num_ctx"},
            )

        def get_llm(self, request):
            self.called = True
            return object()

    provider = FakeProvider()
    core_settings = _FakeCoreSettings(
        {
            "compile": LLMWorkflowProfile(
                common_options={"top_k": 10},
            )
        }
    )

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.resolve_llm_provider",
        lambda: (provider, core_settings),
    )

    with pytest.raises(LLMConfigurationError, match="Unsupported LLM options"):
        resolve_chat_model("compile", "fallback-model")

    assert provider.called is False


def test_resolve_chat_model_rejects_missing_structured_output_support(
    monkeypatch,
) -> None:
    class FakeProvider:
        def __init__(self) -> None:
            self.called = False

        def get_capabilities(self) -> LLMProviderCapabilities:
            return LLMProviderCapabilities(
                provider_name="FakeProvider",
                supports_structured_output=False,
                supported_common_options={"temperature"},
                supported_provider_options=set(),
            )

        def get_llm(self, request):
            self.called = True
            return object()

    provider = FakeProvider()
    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.resolve_llm_provider",
        lambda: (provider, _FakeCoreSettings({})),
    )

    with pytest.raises(
        LLMConfigurationError,
        match="does not support structured output",
    ):
        resolve_chat_model(
            "compile",
            "fallback-model",
            target_name="compile.review",
            requires_structured_output=True,
        )

    assert provider.called is False


def test_invoke_structured_stage_rejects_missing_structured_output_support(
    monkeypatch,
) -> None:
    class FakeProvider:
        def get_capabilities(self) -> LLMProviderCapabilities:
            return LLMProviderCapabilities(
                provider_name="FakeProvider",
                supports_structured_output=False,
                supported_common_options={"temperature"},
                supported_provider_options=set(),
            )

        def get_structured_llm(self, schema, request):
            raise AssertionError("structured runnable should not be requested")

    class FakeSchema:
        pass

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.resolve_llm_provider",
        lambda: (FakeProvider(), _FakeCoreSettings({})),
    )

    with pytest.raises(LLMConfigurationError, match="compile.review"):
        invoke_structured_stage(
            schema=FakeSchema,
            workflow_name="compile",
            fallback_model_name="fallback-model",
            target_name="compile.review",
            system_prompt="system",
            user_prompt="user",
        )


def test_invoke_text_stage_rejects_unsupported_strict_options(monkeypatch) -> None:
    from waygate_core.config.schema import LLMWorkflowProfile

    class FakeProvider:
        def get_capabilities(self) -> LLMProviderCapabilities:
            return LLMProviderCapabilities(
                provider_name="OllamaProvider",
                supports_structured_output=True,
                supported_common_options={"temperature"},
                supported_provider_options={"num_ctx"},
            )

        def get_llm(self, request):
            raise AssertionError("text runnable should not be requested")

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.resolve_llm_provider",
        lambda: (
            FakeProvider(),
            _FakeCoreSettings(
                {
                    "compile": LLMWorkflowProfile(
                        common_options={"top_k": 10},
                    )
                }
            ),
        ),
    )

    with pytest.raises(LLMConfigurationError, match="Unsupported LLM options"):
        invoke_text_stage(
            workflow_name="compile",
            fallback_model_name="fallback-model",
            system_prompt="system",
            user_prompt="user",
        )


def test_invoke_text_stage_uses_active_ollama_provider_from_app_context(
    monkeypatch,
) -> None:
    from waygate_core.config.schema import CoreSettings, LLMWorkflowProfile
    from waygate_plugin_provider_ollama import plugin as ollama_plugin_module

    created: list[tuple[str, dict[str, object]]] = []
    invoked_messages: list[list[object]] = []

    class FakeChatOllama:
        def __init__(self, model: str, **kwargs) -> None:
            created.append((model, kwargs))

        def invoke(self, messages: list[object]) -> object:
            invoked_messages.append(messages)
            return SimpleNamespace(content="generated draft")

    monkeypatch.setattr(ollama_plugin_module, "ChatOllama", FakeChatOllama)

    provider = OllamaProvider(
        config=OllamaProviderConfig(base_url="http://ollama.local")
    )
    core_settings = CoreSettings(
        llm_plugin_name="OllamaProvider",
        llm_workflow_profiles={
            "compile": LLMWorkflowProfile(
                common_options={"temperature": 0.2, "max_tokens": 256},
                provider_options={
                    "OllamaProvider": {
                        "num_ctx": 4096,
                        "validate_model_on_init": True,
                    }
                },
            )
        },
    )
    app_context = SimpleNamespace(
        config=SimpleNamespace(core=core_settings),
        plugins=SimpleNamespace(llm={"OllamaProvider": provider}),
    )

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.get_app_context", lambda: app_context
    )

    result = invoke_text_stage(
        workflow_name="compile",
        fallback_model_name="fallback-model",
        system_prompt="system prompt",
        user_prompt="user prompt",
    )

    assert result == "generated draft"
    assert created == [
        (
            "fallback-model",
            {
                "base_url": "http://ollama.local",
                "validate_model_on_init": True,
                "temperature": 0.2,
                "num_ctx": 4096,
                "num_predict": 256,
            },
        )
    ]
    assert len(invoked_messages) == 1
    assert [message.content for message in invoked_messages[0]] == [
        "system prompt",
        "user prompt",
    ]


def test_invoke_structured_stage_uses_active_ollama_provider_from_app_context(
    monkeypatch,
) -> None:
    from waygate_core.config.schema import CoreSettings, LLMWorkflowProfile
    from waygate_plugin_provider_ollama import plugin as ollama_plugin_module

    created: list[tuple[str, dict[str, object]]] = []
    invoked_messages: list[list[object]] = []

    class FakeStructuredRunnable:
        def invoke(self, messages: list[object]) -> dict[str, str]:
            invoked_messages.append(messages)
            return {"summary": "structured draft"}

    class FakeChatOllama:
        def __init__(self, model: str, **kwargs) -> None:
            created.append((model, kwargs))

        def with_structured_output(
            self, schema: type[BaseModel], **kwargs
        ) -> FakeStructuredRunnable:
            assert schema is _StructuredResult
            assert kwargs == {
                "method": "json_schema",
                "include_raw": True,
            }
            return FakeStructuredRunnable()

    monkeypatch.setattr(ollama_plugin_module, "ChatOllama", FakeChatOllama)

    provider = OllamaProvider(
        config=OllamaProviderConfig(
            base_url="http://ollama.local/",
            validate_model_on_init=True,
        )
    )
    core_settings = CoreSettings(
        llm_plugin_name="OllamaProvider",
        llm_workflow_profiles={
            "compile.review": LLMWorkflowProfile(
                model_name="structured-model",
                provider_options={
                    "OllamaProvider": {
                        "validate_model_on_init": False,
                        "reasoning": True,
                    }
                },
            )
        },
    )
    app_context = SimpleNamespace(
        config=SimpleNamespace(core=core_settings),
        plugins=SimpleNamespace(llm={"OllamaProvider": provider}),
    )

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.get_app_context", lambda: app_context
    )

    result = invoke_structured_stage(
        schema=_StructuredResult,
        workflow_name="compile",
        fallback_model_name="fallback-model",
        target_name="compile.review",
        system_prompt="system prompt",
        user_prompt="user prompt",
    )

    assert result == _StructuredResult(summary="structured draft")
    assert created == [
        (
            "structured-model",
            {
                "base_url": "http://ollama.local",
                "validate_model_on_init": False,
                "reasoning": True,
            },
        )
    ]
    assert len(invoked_messages) == 1
    assert [message.content for message in invoked_messages[0]] == [
        "system prompt",
        "user prompt",
    ]


def test_invoke_structured_stage_recovers_from_ollama_raw_tool_call_payload(
    monkeypatch,
) -> None:
    parsing_error = ValueError("Invalid json output")

    class FakeStructuredRunnable:
        def invoke(self, messages: list[object]) -> dict[str, object]:
            return {
                "raw": SimpleNamespace(
                    content="",
                    additional_kwargs={
                        "tool_calls": [
                            {
                                "function": {
                                    "arguments": '{"summary": "recovered draft"}'
                                }
                            }
                        ]
                    },
                ),
                "parsed": None,
                "parsing_error": parsing_error,
            }

    class FakeProvider:
        def get_capabilities(self) -> LLMProviderCapabilities:
            return LLMProviderCapabilities(
                provider_name="OllamaProvider",
                supports_structured_output=True,
                supported_common_options={"temperature"},
                supported_provider_options=set(),
            )

        def get_structured_llm(self, schema, request):
            return FakeStructuredRunnable()

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.resolve_llm_provider",
        lambda: (FakeProvider(), _FakeCoreSettings({})),
    )

    result = invoke_structured_stage(
        schema=_StructuredResult,
        workflow_name="compile",
        fallback_model_name="fallback-model",
        target_name="compile.review",
        system_prompt="system prompt",
        user_prompt="user prompt",
    )

    assert result == _StructuredResult(summary="recovered draft")


def test_recover_structured_result_recovers_from_raw_agent_message() -> None:
    result = recover_structured_result(
        _StructuredResult,
        {
            "messages": [
                SimpleNamespace(
                    tool_calls=None,
                    additional_kwargs=None,
                    content='{"summary": "recovered from agent"}',
                )
            ]
        },
    )

    assert result == _StructuredResult(summary="recovered from agent")


def test_recover_structured_result_normalizes_legacy_summary_narrative() -> None:
    result = recover_structured_result(
        DocumentAnalysisResultModel,
        {
            "messages": [
                SimpleNamespace(
                    tool_calls=None,
                    additional_kwargs=None,
                    content='{"uri":"file://raw/test.txt","metadata":{"tags":[],"topics":[],"people":[],"organizations":[],"projects":[]},"summary":{"narrative":"Recovered narrative","key_claims":["Claim A"],"defined_terms":["Term A"]},"findings":{"key_claims":["Claim A"],"defined_terms":["Term A"]},"continuity":{"referenced_entities":[],"unresolved_mentions":[]}}',
                )
            ]
        },
    )

    assert result is not None
    assert result.summary.summary == "Recovered narrative"
    assert result.summary.key_claims == ["Claim A"]


def test_recover_structured_result_normalizes_legacy_summary_text() -> None:
    result = recover_structured_result(
        DocumentAnalysisResultModel,
        {
            "messages": [
                SimpleNamespace(
                    tool_calls=None,
                    additional_kwargs=None,
                    content='{"uri":"file://raw/test.txt","metadata":{"tags":[],"topics":[],"people":[],"organizations":[],"projects":[]},"summary":{"text":"Recovered text summary","key_claims":["Claim A"],"defined_terms":["Term A"]},"findings":{"key_claims":["Claim A"],"defined_terms":["Term A"]},"continuity":{"referenced_entities":[],"unresolved_mentions":[]}}',
                )
            ]
        },
    )

    assert result is not None
    assert result.summary.summary == "Recovered text summary"
    assert result.summary.key_claims == ["Claim A"]


def test_recover_structured_result_normalizes_legacy_summary_string() -> None:
    result = recover_structured_result(
        DocumentAnalysisResultModel,
        {
            "messages": [
                SimpleNamespace(
                    tool_calls=None,
                    additional_kwargs=None,
                    content='{"uri":"file://raw/test.txt","metadata":{"tags":[],"topics":[],"people":[],"organizations":[],"projects":[]},"summary":"Recovered bare summary","findings":{"key_claims":["Claim A"],"defined_terms":["Term A"]},"continuity":{"referenced_entities":[],"unresolved_mentions":[]}}',
                )
            ]
        },
    )

    assert result is not None
    assert result.summary.summary == "Recovered bare summary"
    assert result.summary.key_claims == []


def test_recover_structured_result_ignores_unrelated_raw_agent_json() -> None:
    result = recover_structured_result(
        DocumentAnalysisResultModel,
        {
            "messages": [
                SimpleNamespace(
                    tool_calls=None,
                    additional_kwargs=None,
                    content='{"claims":[{"claim_ids":[]}],"unresolved_mentions_subset":[]}',
                )
            ]
        },
    )

    assert result is None


def test_invoke_text_stage_uses_active_featherless_provider_from_app_context(
    monkeypatch,
) -> None:
    from pydantic import SecretStr
    from waygate_core.config.schema import CoreSettings, LLMWorkflowProfile
    from waygate_plugin_provider_featherless_ai import (
        plugin as featherless_plugin_module,
    )

    created: list[dict[str, object]] = []
    invoked_messages: list[list[object]] = []

    class FakeChatOpenAI:
        def __init__(self, **kwargs) -> None:
            created.append(kwargs)

        def invoke(self, messages: list[object]) -> object:
            invoked_messages.append(messages)
            return SimpleNamespace(content="generated featherless draft")

    monkeypatch.setattr(featherless_plugin_module, "ChatOpenAI", FakeChatOpenAI)

    provider = FeatherlessAIProvider(
        config=FeatherlessAIProviderConfig(
            featherless_api_key=SecretStr("test-key"),
            featherless_base_url="https://featherless.invalid/v1/",
        )
    )
    core_settings = CoreSettings(
        llm_plugin_name="FeatherlessAIProvider",
        llm_workflow_profiles={
            "compile": LLMWorkflowProfile(
                common_options={
                    "temperature": 0.2,
                    "top_k": 20,
                    "max_tokens": 256,
                },
                provider_options={
                    "FeatherlessAIProvider": {
                        "presence_penalty": 0.3,
                        "min_p": 0.05,
                    }
                },
            )
        },
    )
    app_context = SimpleNamespace(
        config=SimpleNamespace(core=core_settings),
        plugins=SimpleNamespace(llm={"FeatherlessAIProvider": provider}),
    )

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.get_app_context", lambda: app_context
    )

    result = invoke_text_stage(
        workflow_name="compile",
        fallback_model_name="fallback-model",
        system_prompt="system prompt",
        user_prompt="user prompt",
    )

    assert result == "generated featherless draft"
    assert created == [
        {
            "model": "fallback-model",
            "api_key": "test-key",
            "base_url": "https://featherless.invalid/v1",
            "temperature": 0.2,
            "max_tokens": 256,
            "presence_penalty": 0.3,
            "extra_body": {
                "top_k": 20,
                "min_p": 0.05,
            },
        }
    ]
    assert len(invoked_messages) == 1
    assert [message.content for message in invoked_messages[0]] == [
        "system prompt",
        "user prompt",
    ]


def test_invoke_structured_stage_uses_active_featherless_provider_from_app_context(
    monkeypatch,
) -> None:
    from pydantic import SecretStr
    from waygate_core.config.schema import CoreSettings, LLMWorkflowProfile
    from waygate_plugin_provider_featherless_ai import (
        plugin as featherless_plugin_module,
    )

    created: list[dict[str, object]] = []
    invoked_messages: list[list[object]] = []

    class FakeStructuredRunnable:
        def invoke(self, messages: list[object]) -> dict[str, str]:
            invoked_messages.append(messages)
            return {"summary": "structured featherless draft"}

    class FakeChatOpenAI:
        def __init__(self, **kwargs) -> None:
            created.append(kwargs)

        def with_structured_output(
            self, schema: type[BaseModel]
        ) -> FakeStructuredRunnable:
            assert schema is _StructuredResult
            return FakeStructuredRunnable()

    monkeypatch.setattr(featherless_plugin_module, "ChatOpenAI", FakeChatOpenAI)

    provider = FeatherlessAIProvider(
        config=FeatherlessAIProviderConfig(
            featherless_api_key=SecretStr("test-key"),
            featherless_base_url="https://featherless.invalid/v1",
        )
    )
    core_settings = CoreSettings(
        llm_plugin_name="FeatherlessAIProvider",
        llm_workflow_profiles={
            "compile.review": LLMWorkflowProfile(
                model_name="structured-featherless-model",
                common_options={"temperature": 0.0},
                provider_options={
                    "FeatherlessAIProvider": {
                        "frequency_penalty": 0.4,
                        "include_stop_str_in_output": True,
                    }
                },
            )
        },
    )
    app_context = SimpleNamespace(
        config=SimpleNamespace(core=core_settings),
        plugins=SimpleNamespace(llm={"FeatherlessAIProvider": provider}),
    )

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.get_app_context", lambda: app_context
    )

    result = invoke_structured_stage(
        schema=_StructuredResult,
        workflow_name="compile",
        fallback_model_name="fallback-model",
        target_name="compile.review",
        system_prompt="system prompt",
        user_prompt="user prompt",
    )

    assert result == _StructuredResult(summary="structured featherless draft")
    assert created == [
        {
            "model": "structured-featherless-model",
            "api_key": "test-key",
            "base_url": "https://featherless.invalid/v1",
            "temperature": 0.0,
            "frequency_penalty": 0.4,
            "extra_body": {
                "include_stop_str_in_output": True,
            },
        }
    ]
    assert len(invoked_messages) == 1
    assert [message.content for message in invoked_messages[0]] == [
        "system prompt",
        "user prompt",
    ]


def test_validate_compile_llm_readiness_builds_all_compile_targets(monkeypatch) -> None:
    from waygate_core.config.schema import CoreSettings, LLMWorkflowProfile

    class FakeProvider:
        def __init__(self) -> None:
            self.text_targets: list[tuple[str, str]] = []
            self.structured_targets: list[tuple[str, str, str]] = []

        def get_capabilities(self) -> LLMProviderCapabilities:
            return LLMProviderCapabilities(
                provider_name="OllamaProvider",
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

        def get_llm(self, request):
            self.text_targets.append((request.target_name, request.model_name))
            return object()

        def get_structured_llm(self, schema, request):
            self.structured_targets.append(
                (request.target_name, request.model_name, schema.__name__)
            )
            return object()

    provider = FakeProvider()
    core_settings = CoreSettings(
        llm_plugin_name="OllamaProvider",
        metadata_model_name="metadata-default",
        draft_model_name="draft-default",
        review_model_name="review-default",
        llm_workflow_profiles={
            "compile.source-analysis.summary": LLMWorkflowProfile(
                model_name="summary-override"
            ),
            "compile.review": LLMWorkflowProfile(model_name="review-override"),
        },
    )

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.resolve_llm_provider",
        lambda: (provider, core_settings),
    )

    validate_compile_llm_readiness()

    assert provider.text_targets == [
        ("compile.source-analysis.metadata", "metadata-default"),
        ("compile.source-analysis.summary", "summary-override"),
        ("compile.source-analysis.findings", "draft-default"),
        ("compile.source-analysis.continuity", "draft-default"),
        ("compile.synthesis", "draft-default"),
    ]
    assert provider.structured_targets == [
        (
            "compile.source-analysis.supervisor",
            "draft-default",
            "_PreflightStructuredSchema",
        ),
        ("compile.review", "review-override", "_PreflightStructuredSchema"),
    ]


def test_validate_compile_llm_readiness_wraps_provider_initialization_errors(
    monkeypatch,
) -> None:
    from waygate_core.config.schema import CoreSettings

    class FakeProvider:
        def get_capabilities(self) -> LLMProviderCapabilities:
            return LLMProviderCapabilities(
                provider_name="FakeProvider",
                supports_structured_output=True,
                supported_common_options={
                    "temperature",
                    "top_k",
                    "top_p",
                    "seed",
                    "stop",
                    "max_tokens",
                },
                supported_provider_options=set(),
            )

        def get_llm(self, request):
            raise RuntimeError("provider exploded")

        def get_structured_llm(self, schema, request):
            raise AssertionError("structured target should not be reached")

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.resolve_llm_provider",
        lambda: (
            FakeProvider(),
            CoreSettings(
                llm_plugin_name="FakeProvider",
                metadata_model_name="metadata-default",
                draft_model_name="draft-default",
                review_model_name="review-default",
            ),
        ),
    )

    with pytest.raises(
        LLMConfigurationError,
        match="FakeProvider'.*compile.source-analysis.metadata.*metadata-default.*provider exploded",
    ):
        validate_compile_llm_readiness()


def test_validate_compile_llm_readiness_uses_optional_readiness_probe(
    monkeypatch,
) -> None:
    from waygate_core.config.schema import CoreSettings

    class FakeProvider:
        def __init__(self) -> None:
            self.text_targets: list[tuple[str, str]] = []
            self.structured_targets: list[tuple[str, str, str]] = []

        def get_capabilities(self) -> LLMProviderCapabilities:
            return LLMProviderCapabilities(
                provider_name="FakeProvider",
                supports_structured_output=True,
                supported_common_options={
                    "temperature",
                    "top_k",
                    "top_p",
                    "seed",
                    "stop",
                    "max_tokens",
                },
                supported_provider_options=set(),
            )

        def validate_llm_readiness(self, request) -> None:
            self.text_targets.append((request.target_name, request.model_name))

        def validate_structured_llm_readiness(self, schema, request) -> None:
            self.structured_targets.append(
                (request.target_name, request.model_name, schema.__name__)
            )

        def get_llm(self, request):
            raise AssertionError("fallback get_llm should not be used")

        def get_structured_llm(self, schema, request):
            raise AssertionError("fallback get_structured_llm should not be used")

    provider = FakeProvider()
    core_settings = CoreSettings(
        llm_plugin_name="FakeProvider",
        metadata_model_name="metadata-default",
        draft_model_name="draft-default",
        review_model_name="review-default",
    )

    validate_compile_llm_readiness(provider=provider, core_settings=core_settings)

    assert provider.text_targets == [
        ("compile.source-analysis.metadata", "metadata-default"),
        ("compile.source-analysis.summary", "draft-default"),
        ("compile.source-analysis.findings", "draft-default"),
        ("compile.source-analysis.continuity", "draft-default"),
        ("compile.synthesis", "draft-default"),
    ]
    assert provider.structured_targets == [
        (
            "compile.source-analysis.supervisor",
            "draft-default",
            "_PreflightStructuredSchema",
        ),
        ("compile.review", "review-default", "_PreflightStructuredSchema"),
    ]


def test_validate_compile_llm_readiness_wraps_readiness_probe_errors(
    monkeypatch,
) -> None:
    from waygate_core.config.schema import CoreSettings

    class FakeProvider:
        def get_capabilities(self) -> LLMProviderCapabilities:
            return LLMProviderCapabilities(
                provider_name="FakeProvider",
                supports_structured_output=True,
                supported_common_options={
                    "temperature",
                    "top_k",
                    "top_p",
                    "seed",
                    "stop",
                    "max_tokens",
                },
                supported_provider_options=set(),
            )

        def validate_llm_readiness(self, request) -> None:
            raise RuntimeError("probe exploded")

        def validate_structured_llm_readiness(self, schema, request) -> None:
            raise AssertionError("structured target should not be reached")

        def get_llm(self, request):
            raise AssertionError("fallback get_llm should not be used")

        def get_structured_llm(self, schema, request):
            raise AssertionError("fallback get_structured_llm should not be used")

    with pytest.raises(
        LLMConfigurationError,
        match="FakeProvider'.*readiness validation.*compile.source-analysis.metadata.*metadata-default.*probe exploded",
    ):
        validate_compile_llm_readiness(
            provider=FakeProvider(),
            core_settings=CoreSettings(
                llm_plugin_name="FakeProvider",
                metadata_model_name="metadata-default",
                draft_model_name="draft-default",
                review_model_name="review-default",
            ),
        )


def test_resolve_embeddings_model_uses_active_ollama_provider_from_app_context(
    monkeypatch,
) -> None:
    from waygate_core.config.schema import CoreSettings
    from waygate_plugin_provider_ollama import plugin as ollama_plugin_module

    created: list[tuple[str, dict[str, object]]] = []

    class FakeOllamaEmbeddings:
        def __init__(self, model: str, **kwargs) -> None:
            created.append((model, kwargs))

    monkeypatch.setattr(
        ollama_plugin_module,
        "OllamaEmbeddings",
        FakeOllamaEmbeddings,
    )

    provider = OllamaProvider(
        config=OllamaProviderConfig(base_url="http://ollama.local/")
    )
    core_settings = CoreSettings(llm_plugin_name="OllamaProvider")
    app_context = SimpleNamespace(
        config=SimpleNamespace(core=core_settings),
        plugins=SimpleNamespace(llm={"OllamaProvider": provider}),
    )

    monkeypatch.setattr(
        "waygate_workflows.runtime.llm.get_app_context", lambda: app_context
    )

    result = resolve_embeddings_model("nomic-embed-text")

    assert result is not None
    assert created == [
        (
            "nomic-embed-text",
            {"base_url": "http://ollama.local"},
        )
    ]


def test_resolve_embeddings_model_raises_when_provider_lacks_embeddings() -> None:
    class FakeProvider:
        def get_capabilities(self) -> LLMProviderCapabilities:
            return LLMProviderCapabilities(
                provider_name="FakeProvider",
                supports_structured_output=True,
                supported_common_options=set(),
                supported_provider_options=set(),
            )

    with pytest.raises(
        LLMConfigurationError,
        match="FakeProvider'.*does not support embeddings",
    ):
        resolve_embeddings_model(
            "text-embedding-3-large",
            provider=FakeProvider(),
        )
