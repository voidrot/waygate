from __future__ import annotations

from typing import TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from waygate_core import get_app_context
from waygate_core.plugin import LLMCommonOptions, LLMInvocationRequest

TModel = TypeVar("TModel", bound=BaseModel)


def resolve_llm_provider() -> tuple[object, object]:
    app_context = get_app_context()
    provider_name = app_context.config.core.llm_plugin_name
    provider = app_context.plugins.llm.get(provider_name)
    if provider is None:
        available = ", ".join(sorted(app_context.plugins.llm.keys()))
        raise RuntimeError(
            f"Configured LLM provider '{provider_name}' is unavailable. Installed providers: {available}"
        )
    return provider, app_context.config.core


def build_llm_request(
    workflow_name: str,
    fallback_model_name: str,
) -> LLMInvocationRequest:
    _, core_settings = resolve_llm_provider()
    profile = core_settings.llm_workflow_profiles.get(workflow_name)
    common_options = profile.common_options if profile else LLMCommonOptions()
    provider_options = profile.provider_options if profile else {}
    model_name = (
        profile.model_name if profile and profile.model_name else fallback_model_name
    )
    return LLMInvocationRequest(
        workflow_name=workflow_name,
        model_name=model_name,
        common_options=common_options,
        provider_options=provider_options,
    )


def invoke_structured_stage(
    *,
    schema: type[TModel],
    workflow_name: str,
    fallback_model_name: str,
    system_prompt: str,
    user_prompt: str,
) -> TModel:
    provider, _ = resolve_llm_provider()
    runnable = provider.get_structured_llm(
        schema,
        build_llm_request(workflow_name, fallback_model_name),
    )
    result = runnable.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    if isinstance(result, schema):
        return result
    return schema.model_validate(result)


def invoke_text_stage(
    *,
    workflow_name: str,
    fallback_model_name: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    provider, _ = resolve_llm_provider()
    runnable = provider.get_llm(build_llm_request(workflow_name, fallback_model_name))
    result = runnable.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    content = getattr(result, "content", result)
    if isinstance(content, list):
        return "\n".join(str(item) for item in content).strip()
    return str(content).strip()
