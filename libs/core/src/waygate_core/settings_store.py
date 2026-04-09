from __future__ import annotations

from collections.abc import Callable, Mapping
from importlib import import_module
from typing import Any, Protocol

from waygate_core.doc_helpers import slugify

RUNTIME_SETTINGS_NAMESPACE = "runtime"


class SettingsStore(Protocol):
    def get_namespace(self, namespace: str) -> dict[str, Any]: ...

    def get_value(self, namespace: str, key: str) -> Any | None: ...

    def set_value(self, namespace: str, key: str, value: Any) -> None: ...

    def set_namespace(self, namespace: str, values: Mapping[str, Any]) -> None: ...

    def delete_value(self, namespace: str, key: str) -> None: ...

    def list_namespaces(self) -> list[str]: ...


def build_plugin_settings_namespace(plugin_name: str) -> str:
    normalized = slugify(plugin_name)
    if not normalized:
        raise ValueError("plugin_name must not be empty")
    return f"plugin.{normalized}"


class PostgresSettingsStore:
    def __init__(
        self,
        dsn: str,
        connector: Callable[..., Any] | None = None,
    ):
        if not dsn:
            raise ValueError("dsn must not be empty")
        self.dsn = dsn
        self._connector = connector or self._default_connector

    def _default_connector(self, dsn: str):
        psycopg = import_module("psycopg")
        dict_row = import_module("psycopg.rows").dict_row
        return psycopg.connect(dsn, row_factory=dict_row)

    def _connect(self):
        return self._connector(self.dsn)

    def _ensure_schema(self, conn: Any) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS waygate_settings (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (namespace, key)
            )
            """
        )

    def get_namespace(self, namespace: str) -> dict[str, Any]:
        with self._connect() as conn:
            self._ensure_schema(conn)
            rows = conn.execute(
                """
                SELECT key, value
                FROM waygate_settings
                WHERE namespace = %s
                ORDER BY key
                """,
                (namespace,),
            ).fetchall()
        return {str(row["key"]): row["value"] for row in rows}

    def get_value(self, namespace: str, key: str) -> Any | None:
        with self._connect() as conn:
            self._ensure_schema(conn)
            row = conn.execute(
                """
                SELECT value
                FROM waygate_settings
                WHERE namespace = %s AND key = %s
                """,
                (namespace, key),
            ).fetchone()
        if row is None:
            return None
        return row["value"]

    def set_value(self, namespace: str, key: str, value: Any) -> None:
        Jsonb = import_module("psycopg.types.json").Jsonb

        with self._connect() as conn:
            self._ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO waygate_settings (namespace, key, value)
                VALUES (%s, %s, %s)
                ON CONFLICT (namespace, key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW()
                """,
                (namespace, key, Jsonb(value)),
            )

    def set_namespace(self, namespace: str, values: Mapping[str, Any]) -> None:
        Jsonb = import_module("psycopg.types.json").Jsonb

        with self._connect() as conn:
            self._ensure_schema(conn)
            for key, value in values.items():
                conn.execute(
                    """
                    INSERT INTO waygate_settings (namespace, key, value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (namespace, key)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = NOW()
                    """,
                    (namespace, key, Jsonb(value)),
                )

    def delete_value(self, namespace: str, key: str) -> None:
        with self._connect() as conn:
            self._ensure_schema(conn)
            conn.execute(
                "DELETE FROM waygate_settings WHERE namespace = %s AND key = %s",
                (namespace, key),
            )

    def list_namespaces(self) -> list[str]:
        with self._connect() as conn:
            self._ensure_schema(conn)
            rows = conn.execute(
                "SELECT DISTINCT namespace FROM waygate_settings ORDER BY namespace"
            ).fetchall()
        return [str(row["namespace"]) for row in rows]
