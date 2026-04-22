from __future__ import annotations

from typing import TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from waygate_core import get_app_context
from waygate_core.plugin import (
    LLMCommonOptions,
    LLMConfigurationError,
    LLMEmbeddingsProvider,
    LLMInvocationRequest,
    LLMOptionPolicy,
    LLMReadinessProbe,
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


class _PreflightStructuredSchema(BaseModel):
    """Minimal schema used to preflight structured-output client construction."""

    ok: bool


COMPILE_LLM_PREFLIGHT_TARGETS: tuple[tuple[str, str, bool], ...] = (
    ("compile.source-analysis.metadata", "metadata_model_name", False),
    ("compile.source-analysis.summary", "draft_model_name", False),
    ("compile.source-analysis.findings", "draft_model_name", False),
    ("compile.source-analysis.continuity", "draft_model_name", False),
    ("compile.source-analysis.supervisor", "draft_model_name", False),
    ("compile.synthesis", "draft_model_name", False),
    ("compile.review", "review_model_name", True),
)


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
    """Build an invocation request for one workflow stage."""
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
    """Validate a request against provider capabilities before invocation."""
    capabilities = provider.get_capabilities()
    target_label = request.target_name or request.workflow_name

    if requires_structured_output and not capabilities.supports_structured_output:
        raise LLMConfigurationError(
            "Configured LLM provider "
            f"'{capabilities.provider_name}' does not support structured output "
            f"for target '{target_label}'."
        )

    resolve_invocation_options(request, capabilities)


def resolve_chat_model(
    workflow_name: str,
    fallback_model_name: str,
    *,
    target_name: str | None = None,
    requires_structured_output: bool = False,
):
    """Resolve a chat-capable model runnable for one workflow stage."""
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
        requires_structured_output=requires_structured_output,
    )
    return provider.get_llm(request)


def _build_text_runnable(provider: object, request: LLMInvocationRequest):
    """Build a text runnable and normalize provider construction failures."""
    capabilities = provider.get_capabilities()
    target_label = request.target_name or request.workflow_name
    try:
        return provider.get_llm(request)
    except LLMConfigurationError:
        raise
    except Exception as exc:
        raise LLMConfigurationError(
            "Configured LLM provider "
            f"'{capabilities.provider_name}' failed to initialize target "
            f"'{target_label}' with model '{request.model_name}': {exc}"
        ) from exc


def _probe_text_readiness(provider: object, request: LLMInvocationRequest) -> None:
    """Preflight a text-generation request, using provider-specific hooks when available."""
    if not isinstance(provider, LLMReadinessProbe):
        _build_text_runnable(provider, request)
        return

    capabilities = provider.get_capabilities()
    target_label = request.target_name or request.workflow_name
    try:
        provider.validate_llm_readiness(request)
    except LLMConfigurationError:
        raise
    except Exception as exc:
        raise LLMConfigurationError(
            "Configured LLM provider "
            f"'{capabilities.provider_name}' failed readiness validation for target "
            f"'{target_label}' with model '{request.model_name}': {exc}"
        ) from exc


def _build_structured_runnable(
    provider: object,
    schema: type[TModel],
    request: LLMInvocationRequest,
):
    """Build a structured runnable and normalize provider construction failures."""
    capabilities = provider.get_capabilities()
    target_label = request.target_name or request.workflow_name
    try:
        return provider.get_structured_llm(schema, request)
    except LLMConfigurationError:
        raise
    except Exception as exc:
        raise LLMConfigurationError(
            "Configured LLM provider "
            f"'{capabilities.provider_name}' failed to initialize structured target "
            f"'{target_label}' with model '{request.model_name}': {exc}"
        ) from exc


def _probe_structured_readiness(
    provider: object,
    schema: type[BaseModel],
    request: LLMInvocationRequest,
) -> None:
    """Preflight a structured-output request, using provider-specific hooks when available."""
    if not isinstance(provider, LLMReadinessProbe):
        _build_structured_runnable(provider, schema, request)
        return

    capabilities = provider.get_capabilities()
    target_label = request.target_name or request.workflow_name
    try:
        provider.validate_structured_llm_readiness(schema, request)
    except LLMConfigurationError:
        raise
    except Exception as exc:
        raise LLMConfigurationError(
            "Configured LLM provider "
            f"'{capabilities.provider_name}' failed structured readiness validation for target "
            f"'{target_label}' with model '{request.model_name}': {exc}"
        ) from exc


def validate_compile_llm_readiness(
    *,
    provider: object | None = None,
    core_settings: object | None = None,
) -> None:
    """Preflight the compile workflow's configured LLM requests."""
    if provider is None or core_settings is None:
        provider, core_settings = resolve_llm_provider()

    for (
        target_name,
        fallback_attr,
        requires_structured_output,
    ) in COMPILE_LLM_PREFLIGHT_TARGETS:
        fallback_model_name = getattr(core_settings, fallback_attr)
        request = build_llm_request(
            "compile",
            fallback_model_name,
            target_name=target_name,
            core_settings=core_settings,
        )
        validate_llm_request(
            provider,
            request,
            requires_structured_output=requires_structured_output,
        )
        if requires_structured_output:
            _probe_structured_readiness(provider, _PreflightStructuredSchema, request)
        else:
            _probe_text_readiness(provider, request)


def resolve_embeddings_model(
    model_name: str,
    *,
    provider: object | None = None,
):
    """Resolve an embeddings client from the active provider."""
    if provider is None:
        provider, _ = resolve_llm_provider()

    capabilities = provider.get_capabilities()
    if not isinstance(provider, LLMEmbeddingsProvider):
        raise LLMConfigurationError(
            "Configured LLM provider "
            f"'{capabilities.provider_name}' does not support embeddings."
        )

    try:
        return provider.get_embeddings(model_name)
    except LLMConfigurationError:
        raise
    except Exception as exc:
        raise LLMConfigurationError(
            "Configured LLM provider "
            f"'{capabilities.provider_name}' failed to initialize embeddings model "
            f"'{model_name}': {exc}"
        ) from exc


def _resolve_llm_profile(
    core_settings: object,
    workflow_name: str,
    target_name: str | None,
):
    """Resolve a merged LLM profile for one workflow target."""
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
    """Invoke a structured LLM stage and coerce the response into a schema."""
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
    runnable = _build_structured_runnable(provider, schema, request)
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
    """Invoke a text-generating LLM stage."""
    provider, core_settings = resolve_llm_provider()
    request = build_llm_request(
        workflow_name,
        fallback_model_name,
        target_name=target_name,
        core_settings=core_settings,
    )
    validate_llm_request(provider, request)
    runnable = _build_text_runnable(provider, request)
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
