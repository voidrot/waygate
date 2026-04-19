from __future__ import annotations

from typing import TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from waygate_core import get_app_context
from waygate_core.plugin import (
    LLMCommonOptions,
    LLMConfigurationError,
    LLMInvocationRequest,
    LLMOptionPolicy,
    resolve_invocation_options,
)


COMPILE_TARGET_LEGACY_PROFILE_KEYS: dict[str, str] = {
    "compile.source-analysis.metadata": "metadata",
    "compile.source-analysis.summary": "draft",
    "compile.source-analysis.findings": "draft",
    "compile.source-analysis.continuity": "draft",
    "compile.source-analysis.supervisor": "draft",
    "compile.synthesis": "draft",
    "compile.review": "review",
}

TModel = TypeVar("TModel", bound=BaseModel)


def resolve_llm_provider() -> tuple[object, object]:
    """Resolve the configured LLM provider plugin and core settings.

    Returns:
        Tuple of the active LLM provider instance and core settings object.

    Raises:
        RuntimeError: If the configured provider name is unavailable.
    """
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
    *,
    target_name: str | None = None,
    core_settings: object | None = None,
) -> LLMInvocationRequest:
    """Build an invocation request for one workflow stage.

    Args:
        workflow_name: Logical workflow or stage name.
        fallback_model_name: Default model to use when the workflow profile does
            not override it.
        target_name: Optional exact role or target identifier within a workflow.
        core_settings: Optional pre-resolved core settings to reuse.

    Returns:
        Provider-agnostic invocation request with resolved profile settings.
    """
    if core_settings is None:
        _, core_settings = resolve_llm_provider()
    profile = _resolve_llm_profile(core_settings, workflow_name, target_name)
    common_options = profile.common_options if profile else LLMCommonOptions()
    provider_options = profile.provider_options if profile else {}
    option_policy = profile.option_policy if profile else LLMOptionPolicy.STRICT
    model_name = (
        profile.model_name if profile and profile.model_name else fallback_model_name
    )
    return LLMInvocationRequest(
        workflow_name=workflow_name,
        target_name=target_name,
        model_name=model_name,
        common_options=common_options,
        provider_options=provider_options,
        option_policy=option_policy,
    )


def validate_llm_request(
    provider: object,
    request: LLMInvocationRequest,
    *,
    requires_structured_output: bool = False,
) -> None:
    """Validate a request against provider capabilities before invocation.

    Args:
        provider: Active provider plugin instance.
        request: Request built for the workflow stage or target.
        requires_structured_output: Whether the caller requires structured
            output support from the provider.

    Raises:
        LLMConfigurationError: If the provider cannot satisfy the request.
    """

    capabilities = provider.get_capabilities()
    target_label = request.target_name or request.workflow_name

    if requires_structured_output and not capabilities.supports_structured_output:
        raise LLMConfigurationError(
            "Configured LLM provider "
            f"'{capabilities.provider_name}' does not support structured output "
            f"for target '{target_label}'."
        )

    resolve_invocation_options(request, capabilities)


def _resolve_llm_profile(
    core_settings: object,
    workflow_name: str,
    target_name: str | None,
):
    """Resolve a merged LLM profile for one workflow target.

    Resolution order is low to high precedence so role-specific settings can
    override workflow defaults while still inheriting broader values.

    Args:
        core_settings: Resolved core settings object.
        workflow_name: Logical workflow name.
        target_name: Optional exact role identifier.

    Returns:
        A merged workflow profile, or ``None`` when no profile matches.
    """

    profiles = getattr(core_settings, "llm_workflow_profiles", {})
    matched_profiles = [
        profiles[key]
        for key in _iter_profile_keys(workflow_name, target_name)
        if key in profiles
    ]
    if not matched_profiles:
        return None
    return _merge_llm_profiles(matched_profiles)


def _iter_profile_keys(workflow_name: str, target_name: str | None) -> list[str]:
    """Return profile lookup keys ordered from lowest to highest precedence."""

    keys: list[str] = []
    legacy_key = COMPILE_TARGET_LEGACY_PROFILE_KEYS.get(target_name or "")
    if legacy_key:
        keys.append(legacy_key)
    if workflow_name not in keys:
        keys.append(workflow_name)
    if target_name and target_name not in keys:
        keys.append(target_name)
    return keys


def _merge_llm_profiles(profiles: list[object]):
    """Merge multiple workflow profiles from low to high precedence."""

    model_name: str | None = None
    common_options: dict[str, object] = {}
    provider_options: dict[str, dict[str, object]] = {}
    option_policy = LLMOptionPolicy.STRICT

    for profile in profiles:
        fields_set = getattr(profile, "model_fields_set", set())

        if "model_name" in fields_set and profile.model_name is not None:
            model_name = profile.model_name
        if "common_options" in fields_set:
            common_options.update(profile.common_options.model_dump(exclude_none=True))
        if "provider_options" in fields_set:
            for provider_name, values in profile.provider_options.items():
                provider_options.setdefault(provider_name, {}).update(values)
        if "option_policy" in fields_set:
            option_policy = profile.option_policy

    profile_type = type(profiles[-1])
    return profile_type(
        model_name=model_name,
        common_options=LLMCommonOptions(**common_options),
        provider_options=provider_options,
        option_policy=option_policy,
    )


def invoke_structured_stage(
    *,
    schema: type[TModel],
    workflow_name: str,
    fallback_model_name: str,
    target_name: str | None = None,
    system_prompt: str,
    user_prompt: str,
) -> TModel:
    """Invoke a structured LLM stage and coerce the response into a schema.

    Args:
        schema: Pydantic model expected from the provider.
        workflow_name: Logical workflow or stage name.
        fallback_model_name: Default model name when no profile override exists.
        target_name: Optional exact role or target identifier.
        system_prompt: Instruction prompt for the stage.
        user_prompt: User payload for the stage.

    Returns:
        Structured model instance returned by the provider.
    """
    provider, core_settings = resolve_llm_provider()
    request = build_llm_request(
        workflow_name,
        fallback_model_name,
        target_name=target_name,
        core_settings=core_settings,
    )
    validate_llm_request(
        provider,
        request,
        requires_structured_output=True,
    )
    runnable = provider.get_structured_llm(
        schema,
        request,
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
    target_name: str | None = None,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Invoke a text-generating LLM stage.

    Args:
        workflow_name: Logical workflow or stage name.
        fallback_model_name: Default model name when no profile override exists.
        target_name: Optional exact role or target identifier.
        system_prompt: Instruction prompt for the stage.
        user_prompt: User payload for the stage.

    Returns:
        Final text content extracted from the provider response.
    """
    provider, core_settings = resolve_llm_provider()
    request = build_llm_request(
        workflow_name,
        fallback_model_name,
        target_name=target_name,
        core_settings=core_settings,
    )
    validate_llm_request(provider, request)
    runnable = provider.get_llm(request)
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
