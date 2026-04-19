from __future__ import annotations

import pytest

from waygate_core.plugin import LLMOptionPolicy
from waygate_core.plugin import LLMConfigurationError
from waygate_core.plugin import LLMProviderCapabilities
from waygate_workflows.agents.review import review_draft_with_specialist
from waygate_workflows.agents.common import resolve_chat_model
from waygate_workflows.agents.synthesis import synthesize_draft_with_specialist
from waygate_workflows.tools.llm import build_llm_request
from waygate_workflows.tools.llm import invoke_text_stage
from waygate_workflows.tools.llm import invoke_structured_stage


class _FakeCoreSettings:
    def __init__(self, llm_workflow_profiles: dict[str, object]) -> None:
        self.llm_workflow_profiles = llm_workflow_profiles
        self.llm_plugin_name = "OllamaProvider"


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
        "waygate_workflows.tools.llm.resolve_llm_provider",
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
        "waygate_workflows.tools.llm.resolve_llm_provider",
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

    def fake_resolve_chat_model(
        workflow_name: str,
        fallback_model_name: str,
        *,
        target_name: str | None = None,
        requires_structured_output: bool = False,
    ) -> object:
        resolved_models.append((workflow_name, fallback_model_name, target_name))
        return object()

    class FakeMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class FakeSynthesisAgent:
        def invoke(self, payload: dict[str, object]) -> dict[str, object]:
            return {"messages": [FakeMessage("# Draft")]}

    class FakeReviewAgent:
        def invoke(self, payload: dict[str, object]) -> dict[str, object]:
            return {"structured_response": {"approved": True, "feedback": []}}

    create_agent_results = iter([FakeSynthesisAgent(), FakeReviewAgent()])

    monkeypatch.setattr(
        "waygate_workflows.agents.synthesis.resolve_chat_model",
        fake_resolve_chat_model,
    )
    monkeypatch.setattr(
        "waygate_workflows.agents.review.resolve_chat_model",
        fake_resolve_chat_model,
    )
    monkeypatch.setattr(
        "waygate_workflows.agents.synthesis.create_agent",
        lambda **kwargs: next(create_agent_results),
    )
    monkeypatch.setattr(
        "waygate_workflows.agents.review.create_agent",
        lambda **kwargs: next(create_agent_results),
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
        "waygate_workflows.agents.common.resolve_llm_provider",
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
        "waygate_workflows.agents.common.resolve_llm_provider",
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
        "waygate_workflows.tools.llm.resolve_llm_provider",
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
        "waygate_workflows.tools.llm.resolve_llm_provider",
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
