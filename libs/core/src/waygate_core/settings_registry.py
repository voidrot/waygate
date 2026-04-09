from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field, TypeAdapter

from waygate_core.settings import RuntimeSettings
from waygate_core.settings_store import RUNTIME_SETTINGS_NAMESPACE

SettingValueType = Literal["string", "integer", "boolean", "string_list"]
SettingSource = Literal["stored", "env", "default"]

_STRING_ADAPTER = TypeAdapter(str)
_INTEGER_ADAPTER = TypeAdapter(int)
_BOOLEAN_ADAPTER = TypeAdapter(bool)
_STRING_LIST_ADAPTER = TypeAdapter(list[str])


class SettingDefinition(BaseModel):
    key: str
    title: str
    env_var: str | None = None
    description: str | None = None
    value_type: SettingValueType = "string"
    default_value: Any = None
    secret: bool = False
    editable: bool = True


class SettingsNamespaceDefinition(BaseModel):
    namespace: str
    title: str
    owner: Literal["core", "plugin"]
    plugin_name: str | None = None
    settings: list[SettingDefinition] = Field(default_factory=list)


class ResolvedSetting(BaseModel):
    key: str
    value: Any = None
    source: SettingSource


class SettingsNamespaceRegistry:
    def __init__(
        self,
        definitions: Iterable[SettingsNamespaceDefinition] | None = None,
    ) -> None:
        self._definitions: dict[str, SettingsNamespaceDefinition] = {}
        if definitions is not None:
            for definition in definitions:
                self.register_namespace(definition)

    def register_namespace(self, definition: SettingsNamespaceDefinition) -> None:
        self._definitions[definition.namespace] = definition

    def get_namespace(self, namespace: str) -> SettingsNamespaceDefinition | None:
        return self._definitions.get(namespace)

    def list_namespaces(self) -> list[SettingsNamespaceDefinition]:
        return [self._definitions[key] for key in sorted(self._definitions)]


def build_core_runtime_namespace_definition() -> SettingsNamespaceDefinition:
    defaults = RuntimeSettings().model_dump(mode="json")

    def setting(
        *,
        key: str,
        title: str,
        env_var: str,
        description: str,
        value_type: SettingValueType = "string",
        secret: bool = False,
    ) -> SettingDefinition:
        return SettingDefinition(
            key=key,
            title=title,
            env_var=env_var,
            description=description,
            value_type=value_type,
            default_value=defaults[key],
            secret=secret,
        )

    return SettingsNamespaceDefinition(
        namespace=RUNTIME_SETTINGS_NAMESPACE,
        title="Runtime settings",
        owner="core",
        settings=[
            setting(
                key="storage_provider",
                title="Storage provider",
                env_var="STORAGE_PROVIDER",
                description="Storage provider key used for raw, live, and maintenance writes.",
            ),
            setting(
                key="local_storage_path",
                title="Local storage path",
                env_var="LOCAL_STORAGE_PATH",
                description="Root path for the local storage provider.",
            ),
            setting(
                key="redis_url",
                title="Redis URL",
                env_var="REDIS_URL",
                description="Redis or Valkey connection string for compiler queueing.",
            ),
            setting(
                key="draft_queue_name",
                title="Draft queue name",
                env_var="DRAFT_QUEUE_NAME",
                description="RQ queue name used for compiler draft jobs.",
            ),
            setting(
                key="draft_llm_provider",
                title="Draft LLM provider",
                env_var="DRAFT_LLM_PROVIDER",
                description="Provider key used by the draft node.",
            ),
            setting(
                key="draft_llm_model",
                title="Draft LLM model",
                env_var="DRAFT_LLM_MODEL",
                description="Model identifier used by the draft node.",
            ),
            setting(
                key="review_llm_provider",
                title="Review LLM provider",
                env_var="REVIEW_LLM_PROVIDER",
                description="Provider key used by the review node.",
            ),
            setting(
                key="review_llm_model",
                title="Review LLM model",
                env_var="REVIEW_LLM_MODEL",
                description="Model identifier used by the review node.",
            ),
            setting(
                key="mcp_server_host",
                title="MCP server host",
                env_var="MCP_SERVER_HOST",
                description="Bind host for the MCP HTTP server.",
            ),
            setting(
                key="mcp_server_port",
                title="MCP server port",
                env_var="MCP_SERVER_PORT",
                description="Bind port for the MCP HTTP server.",
                value_type="integer",
            ),
            setting(
                key="mcp_server_path",
                title="MCP server path",
                env_var="MCP_SERVER_PATH",
                description="Mount path for the MCP HTTP transport.",
            ),
            setting(
                key="mcp_auth_enabled",
                title="MCP auth enabled",
                env_var="MCP_AUTH_ENABLED",
                description="Whether static bearer auth is enabled on the MCP service.",
                value_type="boolean",
            ),
            setting(
                key="mcp_auth_token",
                title="MCP auth token",
                env_var="MCP_AUTH_TOKEN",
                description="Static bearer token used by the current MCP auth layer.",
                secret=True,
            ),
            setting(
                key="mcp_default_role",
                title="MCP default role",
                env_var="MCP_DEFAULT_ROLE",
                description="Server-side default role applied to MCP callers.",
            ),
            setting(
                key="mcp_allowed_visibilities",
                title="MCP allowed visibilities",
                env_var="MCP_ALLOWED_VISIBILITIES",
                description="Visibility scopes allowed by default for MCP callers.",
                value_type="string_list",
            ),
            setting(
                key="otel_enabled",
                title="OpenTelemetry enabled",
                env_var="OTEL_ENABLED",
                description="Enables tracing instrumentation for supported services.",
                value_type="boolean",
            ),
            setting(
                key="otel_exporter",
                title="OpenTelemetry exporter",
                env_var="OTEL_EXPORTER",
                description="Exporter key for OpenTelemetry spans.",
            ),
            setting(
                key="otel_service_namespace",
                title="OpenTelemetry service namespace",
                env_var="OTEL_SERVICE_NAMESPACE",
                description="Namespace applied to emitted telemetry service names.",
            ),
        ],
    )


def coerce_setting_value(value: Any, definition: SettingDefinition) -> Any:
    if definition.value_type == "integer":
        return _INTEGER_ADAPTER.validate_python(value)
    if definition.value_type == "boolean":
        return _BOOLEAN_ADAPTER.validate_python(value)
    if definition.value_type == "string_list":
        return _STRING_LIST_ADAPTER.validate_python(value)
    return _STRING_ADAPTER.validate_python(value)


def parse_env_setting_value(
    raw_value: str | None,
    definition: SettingDefinition,
) -> Any | None:
    if raw_value is None:
        return None
    if definition.value_type == "string_list":
        return [item.strip() for item in raw_value.split(",") if item.strip()]
    return coerce_setting_value(raw_value, definition)


def resolve_settings_values(
    definitions: Iterable[SettingDefinition],
    stored_values: Mapping[str, Any],
    *,
    runtime_backend: str,
) -> dict[str, ResolvedSetting]:
    use_stored_values = runtime_backend.lower().strip() == "postgres"
    resolved: dict[str, ResolvedSetting] = {}

    for definition in definitions:
        raw_env_value = os.getenv(definition.env_var) if definition.env_var else None
        env_value = parse_env_setting_value(raw_env_value, definition)
        stored_value = stored_values.get(definition.key)

        if use_stored_values and definition.key in stored_values:
            resolved[definition.key] = ResolvedSetting(
                key=definition.key,
                value=coerce_setting_value(stored_value, definition),
                source="stored",
            )
            continue

        if raw_env_value is not None:
            resolved[definition.key] = ResolvedSetting(
                key=definition.key,
                value=env_value,
                source="env",
            )
            continue

        resolved[definition.key] = ResolvedSetting(
            key=definition.key,
            value=definition.default_value,
            source="default",
        )

    return resolved
