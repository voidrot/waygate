from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from receiver.core.registry import IngestionPlugin
from waygate_core.settings import reload_runtime_settings
from waygate_core.settings_registry import (
    ResolvedSetting,
    SettingDefinition,
    SettingsNamespaceDefinition,
    SettingsNamespaceRegistry,
    build_core_runtime_namespace_definition,
    coerce_setting_value,
    resolve_settings_values,
)
from waygate_core.settings_store import (
    SettingsStore,
    build_plugin_settings_namespace,
)


class SettingsNamespaceSummary(BaseModel):
    namespace: str
    title: str
    owner: str
    plugin_name: str | None = None
    settings_count: int


class SettingsEntryView(BaseModel):
    key: str
    title: str
    description: str | None = None
    value_type: str
    editable: bool
    secret: bool
    default_value: Any = None
    stored: bool
    stored_value: Any = None
    effective_source: str
    effective_value: Any = None


class SettingsNamespaceView(BaseModel):
    namespace: str
    title: str
    owner: str
    plugin_name: str | None = None
    settings: list[SettingsEntryView]


def build_settings_namespace_registry(
    plugins: Mapping[str, IngestionPlugin],
) -> SettingsNamespaceRegistry:
    namespace_registry = SettingsNamespaceRegistry(
        [build_core_runtime_namespace_definition()]
    )
    for plugin_name in sorted(plugins):
        plugin = plugins[plugin_name]
        definitions = list(plugin.settings_definitions)
        if not definitions:
            continue
        namespace_registry.register_namespace(
            SettingsNamespaceDefinition(
                namespace=build_plugin_settings_namespace(plugin.plugin_name),
                title=f"{plugin.plugin_name.replace('_', ' ').title()} settings",
                owner="plugin",
                plugin_name=plugin.plugin_name,
                settings=definitions,
            )
        )
    return namespace_registry


class SettingsAdminService:
    def __init__(
        self,
        *,
        namespace_registry: SettingsNamespaceRegistry,
        runtime_settings_backend: str,
        store: SettingsStore | None,
    ) -> None:
        self._namespace_registry = namespace_registry
        self._runtime_settings_backend = runtime_settings_backend
        self._store = store

    def list_namespaces(self) -> list[SettingsNamespaceSummary]:
        return [
            SettingsNamespaceSummary(
                namespace=definition.namespace,
                title=definition.title,
                owner=definition.owner,
                plugin_name=definition.plugin_name,
                settings_count=len(definition.settings),
            )
            for definition in self._namespace_registry.list_namespaces()
        ]

    def get_namespace(self, namespace: str) -> SettingsNamespaceView:
        definition = self._require_definition(namespace)
        stored_values = self._load_stored_values(namespace)
        resolved_values = resolve_settings_values(
            definition.settings,
            stored_values,
            runtime_backend=self._runtime_settings_backend,
        )
        return SettingsNamespaceView(
            namespace=definition.namespace,
            title=definition.title,
            owner=definition.owner,
            plugin_name=definition.plugin_name,
            settings=[
                self._build_entry_view(
                    definition=setting,
                    stored_values=stored_values,
                    resolved=resolved_values[setting.key],
                )
                for setting in definition.settings
            ],
        )

    def update_namespace(
        self,
        namespace: str,
        values: Mapping[str, Any],
    ) -> SettingsNamespaceView:
        if self._store is None:
            raise RuntimeError(
                "POSTGRES_DSN must be configured before persisted settings can be updated"
            )

        definition = self._require_definition(namespace)
        definitions_by_key = {setting.key: setting for setting in definition.settings}

        for key, value in values.items():
            setting = definitions_by_key.get(key)
            if setting is None:
                raise KeyError(f"Unknown setting '{key}' for namespace '{namespace}'")
            if value is None:
                self._store.delete_value(namespace, key)
                continue
            self._store.set_value(namespace, key, coerce_setting_value(value, setting))

        if namespace == "runtime" and self._runtime_settings_backend == "postgres":
            reload_runtime_settings()

        return self.get_namespace(namespace)

    def _require_definition(self, namespace: str) -> SettingsNamespaceDefinition:
        definition = self._namespace_registry.get_namespace(namespace)
        if definition is None:
            raise KeyError(f"Unknown settings namespace '{namespace}'")
        return definition

    def _load_stored_values(self, namespace: str) -> dict[str, Any]:
        if self._store is None:
            return {}
        return self._store.get_namespace(namespace)

    def _build_entry_view(
        self,
        *,
        definition: SettingDefinition,
        stored_values: Mapping[str, Any],
        resolved: ResolvedSetting,
    ) -> SettingsEntryView:
        return SettingsEntryView(
            key=definition.key,
            title=definition.title,
            description=definition.description,
            value_type=definition.value_type,
            editable=definition.editable,
            secret=definition.secret,
            default_value=None if definition.secret else definition.default_value,
            stored=definition.key in stored_values,
            stored_value=self._visible_value(
                definition=definition,
                value=stored_values.get(definition.key),
            ),
            effective_source=resolved.source,
            effective_value=self._visible_value(
                definition=definition, value=resolved.value
            ),
        )

    def _visible_value(self, *, definition: SettingDefinition, value: Any) -> Any:
        if value is None or definition.secret:
            return None
        return value
