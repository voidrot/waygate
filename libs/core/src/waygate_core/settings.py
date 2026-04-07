from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field


class RuntimeSettings(BaseModel):
    storage_provider: str = Field(default="local")
    local_storage_path: str = Field(default="wiki")

    redis_url: str = Field(default="redis://localhost:6379/0")
    draft_queue_name: str = Field(default="draft_tasks")

    draft_llm_provider: str = Field(default="ollama")
    draft_llm_model: str = Field(default="gemma4:e4b")
    review_llm_provider: str = Field(default="ollama")
    review_llm_model: str = Field(default="hermes3:8b")

    mcp_server_host: str = Field(default="127.0.0.1")
    mcp_server_port: int = Field(default=8000)
    mcp_server_path: str = Field(default="/mcp")
    mcp_auth_enabled: bool = Field(default=False)
    mcp_auth_token: str | None = Field(default=None)
    mcp_default_role: str | None = Field(default=None)
    mcp_allowed_visibilities: list[str] = Field(
        default_factory=lambda: ["public", "internal"]
    )
    otel_enabled: bool = Field(default=False)
    otel_exporter: str = Field(default="console")
    otel_service_namespace: str = Field(default="waygate")


def _parse_csv_env(raw_value: str | None, default: list[str]) -> list[str]:
    if raw_value is None:
        return default
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    return values or default


def _load_runtime_env() -> dict[str, object]:
    return {
        "storage_provider": os.getenv("STORAGE_PROVIDER", "local"),
        "local_storage_path": os.getenv("LOCAL_STORAGE_PATH", "wiki"),
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "draft_queue_name": os.getenv("DRAFT_QUEUE_NAME", "draft_tasks"),
        "draft_llm_provider": os.getenv("DRAFT_LLM_PROVIDER", "ollama"),
        "draft_llm_model": os.getenv("DRAFT_LLM_MODEL", "gemma4:e4b"),
        "review_llm_provider": os.getenv("REVIEW_LLM_PROVIDER", "ollama"),
        "review_llm_model": os.getenv("REVIEW_LLM_MODEL", "hermes3:8b"),
        "mcp_server_host": os.getenv("MCP_SERVER_HOST", "127.0.0.1"),
        "mcp_server_port": os.getenv("MCP_SERVER_PORT", "8000"),
        "mcp_server_path": os.getenv("MCP_SERVER_PATH", "/mcp"),
        "mcp_auth_enabled": os.getenv("MCP_AUTH_ENABLED", "false"),
        "mcp_auth_token": os.getenv("MCP_AUTH_TOKEN"),
        "mcp_default_role": os.getenv("MCP_DEFAULT_ROLE"),
        "mcp_allowed_visibilities": _parse_csv_env(
            os.getenv("MCP_ALLOWED_VISIBILITIES"),
            ["public", "internal"],
        ),
        "otel_enabled": os.getenv("OTEL_ENABLED", "false"),
        "otel_exporter": os.getenv("OTEL_EXPORTER", "console"),
        "otel_service_namespace": os.getenv(
            "OTEL_SERVICE_NAMESPACE", "waygate"
        ),
    }


@lru_cache(maxsize=1)
def get_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings.model_validate(_load_runtime_env())


def reload_runtime_settings() -> RuntimeSettings:
    get_runtime_settings.cache_clear()
    return get_runtime_settings()
