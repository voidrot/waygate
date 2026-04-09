from __future__ import annotations

from typing import Any

from waygate_core.settings_store import (
    PostgresSettingsStore,
    RUNTIME_SETTINGS_NAMESPACE,
    build_plugin_settings_namespace,
)


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def fetchall(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def fetchone(self) -> dict[str, Any] | None:
        if not self._rows:
            return None
        return self._rows[0]


class FakeConnection:
    def __init__(self):
        self.entries: dict[tuple[str, str], Any] = {}

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> FakeResult:
        normalized = " ".join(query.split())
        if normalized.startswith("CREATE TABLE IF NOT EXISTS waygate_settings"):
            return FakeResult([])

        if normalized.startswith(
            "INSERT INTO waygate_settings (namespace, key, value)"
        ):
            assert params is not None
            namespace, key, value = params
            stored_value = getattr(value, "obj", value)
            self.entries[(str(namespace), str(key))] = stored_value
            return FakeResult([])

        if normalized.startswith(
            "SELECT key, value FROM waygate_settings WHERE namespace = %s"
        ):
            assert params is not None
            namespace = str(params[0])
            rows = [
                {"key": key, "value": value}
                for (entry_namespace, key), value in sorted(self.entries.items())
                if entry_namespace == namespace
            ]
            return FakeResult(rows)

        if normalized.startswith(
            "SELECT value FROM waygate_settings WHERE namespace = %s AND key = %s"
        ):
            assert params is not None
            value = self.entries.get((str(params[0]), str(params[1])))
            if value is None:
                return FakeResult([])
            return FakeResult([{"value": value}])

        if normalized.startswith(
            "DELETE FROM waygate_settings WHERE namespace = %s AND key = %s"
        ):
            assert params is not None
            self.entries.pop((str(params[0]), str(params[1])), None)
            return FakeResult([])

        if normalized.startswith(
            "SELECT DISTINCT namespace FROM waygate_settings ORDER BY namespace"
        ):
            namespaces = sorted({namespace for namespace, _ in self.entries})
            return FakeResult([{"namespace": namespace} for namespace in namespaces])

        raise AssertionError(f"Unhandled query: {normalized}")


def test_build_plugin_settings_namespace_slugifies_names() -> None:
    assert (
        build_plugin_settings_namespace("GitHub Receiver") == "plugin.github-receiver"
    )


def test_postgres_settings_store_round_trips_namespaced_values() -> None:
    connection = FakeConnection()
    store = PostgresSettingsStore(
        "postgresql://unused",
        connector=lambda dsn: connection,
    )

    store.set_value(RUNTIME_SETTINGS_NAMESPACE, "redis_url", "redis://db:6379/2")
    store.set_namespace(
        build_plugin_settings_namespace("github_receiver"),
        {
            "webhook_secret": "secret",
            "webhook_enabled": True,
        },
    )

    assert (
        store.get_value(RUNTIME_SETTINGS_NAMESPACE, "redis_url") == "redis://db:6379/2"
    )
    assert store.get_namespace(build_plugin_settings_namespace("github_receiver")) == {
        "webhook_enabled": True,
        "webhook_secret": "secret",
    }
    assert store.list_namespaces() == [
        "plugin.github-receiver",
        "runtime",
    ]


def test_postgres_settings_store_delete_value_removes_entry() -> None:
    connection = FakeConnection()
    store = PostgresSettingsStore(
        "postgresql://unused",
        connector=lambda dsn: connection,
    )

    store.set_value(RUNTIME_SETTINGS_NAMESPACE, "redis_url", "redis://db:6379/2")
    store.delete_value(RUNTIME_SETTINGS_NAMESPACE, "redis_url")

    assert store.get_value(RUNTIME_SETTINGS_NAMESPACE, "redis_url") is None
