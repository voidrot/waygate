from __future__ import annotations

import json
from typing import TypeVar, cast

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from pydantic import ValidationError

from waygate_core import get_app_context
from waygate_core.logging import get_logger
from waygate_core.plugin import (
    LLMCommonOptions,
    LLMConfigurationError,
    LLMEmbeddingsProvider,
    LLMInvocationRequest,
    LLMOptionPolicy,
    LLMReadinessProbe,
    resolve_invocation_options,
)
from waygate_workflows.runtime.text import preview_text

logger = get_logger(__name__)


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
    ("compile.source-analysis.supervisor", "draft_model_name", True),
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
    logger.debug("Resolving LLM provider", provider_name=provider_name)
    provider = app_context.plugins.llm.get(provider_name)
    if provider is None:
        available = ", ".join(sorted(app_context.plugins.llm.keys()))
        logger.error(
            "Configured LLM provider is unavailable",
            provider_name=provider_name,
            available_providers=available,
        )
        raise RuntimeError(
            f"Configured LLM provider '{provider_name}' is unavailable. Installed providers: {available}"
        )
    logger.debug(
        "Resolved LLM provider",
        provider_name=provider_name,
        provider_type=type(provider).__name__,
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
    request = LLMInvocationRequest(
        workflow_name=workflow_name,
        target_name=target_name,
        model_name=model_name,
        common_options=common_options,
        provider_options=provider_options,
        option_policy=option_policy,
    )
    logger.debug(
        "Built LLM request",
        workflow_name=workflow_name,
        target_name=target_name,
        model_name=model_name,
        used_profile=profile is not None,
        option_policy=option_policy.value,
    )
    return request


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
        logger.error(
            "LLM provider does not support required structured output",
            provider_name=capabilities.provider_name,
            target_name=target_label,
            model_name=request.model_name,
        )
        raise LLMConfigurationError(
            "Configured LLM provider "
            f"'{capabilities.provider_name}' does not support structured output "
            f"for target '{target_label}'."
        )

    resolve_invocation_options(request, capabilities)
    logger.debug(
        "Validated LLM request",
        provider_name=capabilities.provider_name,
        target_name=target_label,
        model_name=request.model_name,
        requires_structured_output=requires_structured_output,
    )


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

    logger.info("Starting compile LLM readiness validation")

    for (
        target_name,
        fallback_attr,
        requires_structured_output,
    ) in COMPILE_LLM_PREFLIGHT_TARGETS:
        fallback_model_name = getattr(core_settings, fallback_attr)
        logger.debug(
            "Validating compile LLM target",
            target_name=target_name,
            fallback_model_name=fallback_model_name,
            requires_structured_output=requires_structured_output,
        )
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
    logger.info("Compile LLM readiness validation completed")


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


def _decode_structured_json_candidate(candidate: object) -> object | None:
    """Decode one candidate structured payload when it looks JSON-like."""

    if isinstance(candidate, dict):
        return candidate
    if not isinstance(candidate, str):
        return None

    stripped = candidate.strip()
    if not stripped:
        return None

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _recover_structured_output_from_tool_calls(tool_calls: object) -> object | None:
    """Recover structured payloads from raw tool-call envelopes."""

    if not isinstance(tool_calls, list):
        return None

    for call in tool_calls:
        if not isinstance(call, dict):
            continue

        call_dict = cast(dict[str, object], call)

        args = _decode_structured_json_candidate(call_dict.get("args"))
        if args is not None:
            return args

        function = call_dict.get("function")
        if not isinstance(function, dict):
            continue

        function_dict = cast(dict[str, object], function)

        arguments = _decode_structured_json_candidate(function_dict.get("arguments"))
        if arguments is not None:
            return arguments

    return None


def _recover_structured_output_from_raw_message(raw: object) -> object | None:
    """Recover a structured payload from a raw provider message when parsing failed."""

    tool_calls = getattr(raw, "tool_calls", None)
    recovered = _recover_structured_output_from_tool_calls(tool_calls)
    if recovered is not None:
        return recovered

    additional_kwargs = getattr(raw, "additional_kwargs", None)
    if isinstance(additional_kwargs, dict):
        recovered = _recover_structured_output_from_tool_calls(
            additional_kwargs.get("tool_calls")
        )
        if recovered is not None:
            return recovered

    content = getattr(raw, "content", None)
    if isinstance(content, list):
        content = "\n".join(str(item) for item in content).strip()

    return _decode_structured_json_candidate(content)


def _normalize_legacy_structured_payload(
    schema: type[TModel], payload: object
) -> object:
    """Normalize known legacy structured-output shapes before validation.

    This keeps recovery tolerant of older agent payloads that still emit
    ``summary.narrative`` or ``summary.text`` instead of ``summary.summary``
    in combined document analysis results.
    """

    if not isinstance(payload, dict):
        return payload

    payload_dict = cast(dict[str, object], payload)

    summary_field = schema.model_fields.get("summary")
    if summary_field is None:
        return payload

    summary_annotation = summary_field.annotation
    expects_nested_summary_model = isinstance(summary_annotation, type) and issubclass(
        summary_annotation, BaseModel
    )
    if not expects_nested_summary_model:
        return payload

    summary_value = payload_dict.get("summary")
    if isinstance(summary_value, str):
        normalized = dict(payload_dict)
        normalized["summary"] = {"summary": summary_value}
        logger.warning(
            "Normalized legacy structured summary payload",
            schema_name=schema.__name__,
        )
        return normalized

    if not isinstance(summary_value, dict):
        return payload

    if "summary" in summary_value:
        return payload

    legacy_summary_key = next(
        (key for key in ("narrative", "text") if key in summary_value),
        None,
    )
    if legacy_summary_key is None:
        return payload

    normalized = dict(payload_dict)
    normalized_summary = dict(summary_value)
    normalized_summary["summary"] = str(normalized_summary.pop(legacy_summary_key))
    normalized["summary"] = normalized_summary
    logger.warning(
        "Normalized legacy structured summary payload",
        schema_name=schema.__name__,
    )
    return normalized


def _validate_recovered_payload(schema: type[TModel], payload: object) -> TModel | None:
    """Validate recovered payloads conservatively.

    Recovered raw message content may include arbitrary JSON such as echoed prompt
    context. Ignore candidates that do not contain the target schema's required
    top-level fields instead of raising during supervisor recovery.
    """

    normalized = _normalize_legacy_structured_payload(schema, payload)
    if isinstance(normalized, dict):
        missing_required_fields = [
            field_name
            for field_name, field in schema.model_fields.items()
            if field.is_required() and field_name not in normalized
        ]
        if missing_required_fields:
            logger.debug(
                "Discarded recovered payload missing required schema fields",
                schema_name=schema.__name__,
                missing_required_fields=missing_required_fields,
            )
            return None

    try:
        return schema.model_validate(normalized)
    except ValidationError as exc:
        logger.debug(
            "Discarded recovered payload that failed schema validation",
            schema_name=schema.__name__,
            detail=str(exc),
        )
        return None


def recover_structured_result(schema: type[TModel], result: object) -> TModel | None:
    """Recover a structured result from direct values, provider envelopes, or agent state.

    Args:
        schema: Expected structured response schema.
        result: Raw invocation result from a structured runnable or agent.

    Returns:
        Parsed schema instance when recovery succeeds, otherwise ``None``.
    """

    if isinstance(result, schema):
        return result

    if not isinstance(result, dict):
        return None

    result_dict = cast(dict[str, object], result)

    if {"raw", "parsed", "parsing_error"}.issubset(result_dict):
        parsed = result_dict.get("parsed")
        if parsed is not None:
            if isinstance(parsed, schema):
                return parsed
            return _validate_recovered_payload(schema, parsed)

        recovered = _recover_structured_output_from_raw_message(result_dict.get("raw"))
        if recovered is not None:
            logger.warning(
                "Recovered structured output from raw provider message",
                schema_name=schema.__name__,
            )
            return _validate_recovered_payload(schema, recovered)
        return None

    structured = result_dict.get("structured_response")
    if structured is not None:
        if isinstance(structured, schema):
            return structured
        return _validate_recovered_payload(schema, structured)

    messages = result_dict.get("messages")
    if not isinstance(messages, list):
        return None

    for message in reversed(messages):
        recovered = _recover_structured_output_from_raw_message(message)
        if recovered is None:
            continue
        logger.warning(
            "Recovered structured output from raw agent message",
            schema_name=schema.__name__,
        )
        validated = _validate_recovered_payload(schema, recovered)
        if validated is not None:
            return validated

    return None


def _coerce_structured_stage_result(schema: type[TModel], result: object) -> TModel:
    """Normalize direct or raw-envelope structured results into the target schema."""

    recovered = recover_structured_result(schema, result)
    if recovered is not None:
        return recovered

    if isinstance(result, dict):
        result_dict = cast(dict[str, object], result)
    else:
        result_dict = None

    if result_dict is not None and {"raw", "parsed", "parsing_error"}.issubset(
        result_dict
    ):
        parsing_error = result_dict.get("parsing_error")
        if isinstance(parsing_error, BaseException):
            logger.error(
                "Structured output parsing failed",
                schema_name=schema.__name__,
                detail=str(parsing_error),
            )
            raise parsing_error

    return schema.model_validate(result)


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
    logger.info(
        "Invoking structured LLM stage",
        workflow_name=workflow_name,
        target_name=target_name,
        schema_name=schema.__name__,
        prompt_length=len(user_prompt),
    )
    logger.debug(
        "Structured LLM stage prompt preview",
        workflow_name=workflow_name,
        target_name=target_name,
        prompt_preview=preview_text(user_prompt),
    )
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
    coerced = _coerce_structured_stage_result(schema, result)
    logger.info(
        "Structured LLM stage completed",
        workflow_name=workflow_name,
        target_name=target_name,
        schema_name=schema.__name__,
        result_type=type(coerced).__name__,
    )
    return coerced


def invoke_text_stage(
    *,
    workflow_name: str,
    fallback_model_name: str,
    target_name: str | None = None,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Invoke a text-generating LLM stage."""
    logger.info(
        "Invoking text LLM stage",
        workflow_name=workflow_name,
        target_name=target_name,
        prompt_length=len(user_prompt),
    )
    logger.debug(
        "Text LLM stage prompt preview",
        workflow_name=workflow_name,
        target_name=target_name,
        prompt_preview=preview_text(user_prompt),
    )
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
        text = "\n".join(str(item) for item in content).strip()
    else:
        text = str(content).strip()
    logger.info(
        "Text LLM stage completed",
        workflow_name=workflow_name,
        target_name=target_name,
        response_length=len(text),
    )
    return text
