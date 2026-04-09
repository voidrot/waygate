from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi.testclient import TestClient

from receiver.api import settings as settings_api
from receiver.app import app
from receiver.services.settings import (
    SettingsAdminService,
    build_settings_namespace_registry,
)
from waygate_core.plugin_base import IngestionPlugin
from waygate_core.settings_registry import SettingDefinition


class FakeStore:
    def __init__(self) -> None:
        self.entries: dict[tuple[str, str], Any] = {}

    def get_namespace(self, namespace: str) -> dict[str, Any]:
        return {
            key: value
            for (entry_namespace, key), value in sorted(self.entries.items())
            if entry_namespace == namespace
        }

    def get_value(self, namespace: str, key: str) -> Any | None:
        return self.entries.get((namespace, key))

    def set_value(self, namespace: str, key: str, value: Any) -> None:
        self.entries[(namespace, key)] = value

    def set_namespace(self, namespace: str, values: Mapping[str, Any]) -> None:
        for key, value in values.items():
            self.entries[(namespace, key)] = value

    def delete_value(self, namespace: str, key: str) -> None:
        self.entries.pop((namespace, key), None)

    def list_namespaces(self) -> list[str]:
        return sorted({namespace for namespace, _ in self.entries})


class FakePlugin(IngestionPlugin):
    @property
    def plugin_name(self) -> str:
        return "github_receiver"

    @property
    def settings_definitions(self) -> list[SettingDefinition]:
        return [
            SettingDefinition(
                key="webhook_secret",
                title="Webhook secret",
                env_var="GITHUB_WEBHOOK_SECRET",
                secret=True,
            ),
            SettingDefinition(
                key="export_path",
                title="Export path",
                env_var="GITHUB_EXPORT_PATH",
            ),
        ]


def _build_service(store: FakeStore) -> SettingsAdminService:
    namespace_registry = build_settings_namespace_registry(
        {"github_receiver": FakePlugin()}
    )
    return SettingsAdminService(
        namespace_registry=namespace_registry,
        runtime_settings_backend="postgres",
        store=store,
    )


def test_list_settings_namespaces_includes_core_and_plugin(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://env:6379/0")
    service = _build_service(FakeStore())
    app.dependency_overrides[settings_api.get_settings_service] = lambda: service

    client = TestClient(app)
    response = client.get("/admin/settings")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    namespaces = response.json()["namespaces"]
    assert [entry["namespace"] for entry in namespaces] == [
        "plugin.github-receiver",
        "runtime",
    ]


def test_get_settings_namespace_redacts_secret_values(monkeypatch) -> None:
    store = FakeStore()
    store.set_value("plugin.github-receiver", "webhook_secret", "top-secret")
    store.set_value("plugin.github-receiver", "export_path", "/tmp/github")

    service = _build_service(store)
    app.dependency_overrides[settings_api.get_settings_service] = lambda: service

    client = TestClient(app)
    response = client.get("/admin/settings/plugin.github-receiver")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    entries = {entry["key"]: entry for entry in payload["settings"]}

    assert entries["webhook_secret"]["stored"] is True
    assert entries["webhook_secret"]["stored_value"] is None
    assert entries["webhook_secret"]["effective_value"] is None
    assert entries["export_path"]["stored_value"] == "/tmp/github"


def test_patch_settings_namespace_updates_and_deletes_values(monkeypatch) -> None:
    store = FakeStore()
    store.set_value("runtime", "redis_url", "redis://old:6379/0")
    monkeypatch.setenv("REDIS_URL", "redis://env:6379/0")

    service = _build_service(store)
    app.dependency_overrides[settings_api.get_settings_service] = lambda: service

    client = TestClient(app)
    response = client.patch(
        "/admin/settings/runtime",
        json={"values": {"redis_url": "redis://new:6379/2", "draft_queue_name": None}},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    entries = {entry["key"]: entry for entry in payload["settings"]}

    assert store.get_value("runtime", "redis_url") == "redis://new:6379/2"
    assert entries["redis_url"]["stored_value"] == "redis://new:6379/2"
    assert entries["redis_url"]["effective_source"] == "stored"
    assert store.get_value("runtime", "draft_queue_name") is None


def test_patch_settings_namespace_requires_store(monkeypatch) -> None:
    namespace_registry = build_settings_namespace_registry(
        {"github_receiver": FakePlugin()}
    )
    service = SettingsAdminService(
        namespace_registry=namespace_registry,
        runtime_settings_backend="env",
        store=None,
    )
    app.dependency_overrides[settings_api.get_settings_service] = lambda: service

    client = TestClient(app)
    response = client.patch(
        "/admin/settings/runtime",
        json={"values": {"redis_url": "redis://new:6379/2"}},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "POSTGRES_DSN" in response.json()["detail"]
