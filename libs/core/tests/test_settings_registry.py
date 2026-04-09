import pytest

from waygate_core.settings_registry import (
    SettingDefinition,
    SettingsNamespaceDefinition,
    SettingsNamespaceRegistry,
    build_core_runtime_namespace_definition,
    resolve_settings_values,
)


def test_namespace_registry_lists_sorted_namespaces() -> None:
    registry = SettingsNamespaceRegistry()
    registry.register_namespace(
        SettingsNamespaceDefinition(
            namespace="plugin.zed",
            title="Zed settings",
            owner="plugin",
        )
    )
    registry.register_namespace(
        SettingsNamespaceDefinition(
            namespace="runtime",
            title="Runtime settings",
            owner="core",
        )
    )

    assert [definition.namespace for definition in registry.list_namespaces()] == [
        "plugin.zed",
        "runtime",
    ]


def test_core_runtime_namespace_definition_omits_bootstrap_fields() -> None:
    definition = build_core_runtime_namespace_definition()

    keys = {setting.key for setting in definition.settings}

    assert definition.namespace == "runtime"
    assert "postgres_dsn" not in keys
    assert "runtime_settings_backend" not in keys
    assert "runtime_settings_namespace" not in keys
    assert "redis_url" in keys


def test_resolve_settings_values_prefers_stored_values_when_backend_is_postgres(
    monkeypatch,
) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://env:6379/0")
    definitions = [
        SettingDefinition(
            key="redis_url",
            title="Redis URL",
            env_var="REDIS_URL",
            default_value="redis://default:6379/0",
        )
    ]

    resolved = resolve_settings_values(
        definitions,
        {"redis_url": "redis://db:6379/2"},
        runtime_backend="postgres",
    )

    assert resolved["redis_url"].value == "redis://db:6379/2"
    assert resolved["redis_url"].source == "stored"


def test_resolve_settings_values_uses_env_when_backend_is_env(monkeypatch) -> None:
    monkeypatch.setenv("OTEL_ENABLED", "true")
    definitions = [
        SettingDefinition(
            key="otel_enabled",
            title="OpenTelemetry enabled",
            env_var="OTEL_ENABLED",
            value_type="boolean",
            default_value=False,
        )
    ]

    resolved = resolve_settings_values(
        definitions,
        {"otel_enabled": False},
        runtime_backend="env",
    )

    assert resolved["otel_enabled"].value is True
    assert resolved["otel_enabled"].source == "env"


def test_resolve_settings_values_validates_stored_types() -> None:
    definitions = [
        SettingDefinition(
            key="mcp_server_port",
            title="MCP server port",
            value_type="integer",
            default_value=8000,
        )
    ]

    with pytest.raises(Exception):
        resolve_settings_values(
            definitions,
            {"mcp_server_port": "not-a-port"},
            runtime_backend="postgres",
        )
