from __future__ import annotations

from urllib.parse import quote_plus

from waygate_core import get_app_context


def build_postgres_connection_string() -> str:
    """Build the Postgres checkpoint connection string from core settings.

    Returns:
        URL-encoded Postgres connection string for LangGraph persistence.
    """
    core_settings = get_app_context().config.core
    user = quote_plus(core_settings.pg_user)
    password = quote_plus(core_settings.pg_password)
    database = quote_plus(core_settings.pg_db)
    return (
        f"postgresql://{user}:{password}@{core_settings.pg_host}:"
        f"{core_settings.pg_port}/{database}"
    )
