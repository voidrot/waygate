import pytest

from waygate_core.schemas import Visibility
from waygate_core import settings as settings_module
from waygate_core.settings import reload_runtime_settings


def test_runtime_settings_defaults(monkeypatch) -> None:
    monkeypatch.delenv("STORAGE_PROVIDER", raising=False)
    monkeypatch.delenv("LOCAL_STORAGE_PATH", raising=False)
    monkeypatch.delenv("RUNTIME_SETTINGS_BACKEND", raising=False)
    monkeypatch.delenv("RUNTIME_SETTINGS_NAMESPACE", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("DRAFT_QUEUE_NAME", raising=False)
    monkeypatch.delenv("DRAFT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DRAFT_LLM_MODEL", raising=False)
    monkeypatch.delenv("REVIEW_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("REVIEW_LLM_MODEL", raising=False)
    monkeypatch.delenv("MCP_SERVER_HOST", raising=False)
    monkeypatch.delenv("MCP_SERVER_PORT", raising=False)
    monkeypatch.delenv("MCP_SERVER_PATH", raising=False)
    monkeypatch.delenv("MCP_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("MCP_DEFAULT_ROLE", raising=False)
    monkeypatch.delenv("MCP_ALLOWED_VISIBILITIES", raising=False)
    monkeypatch.delenv("OTEL_ENABLED", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER", raising=False)
    monkeypatch.delenv("OTEL_SERVICE_NAMESPACE", raising=False)

    settings = reload_runtime_settings()

    assert settings.storage_provider == "local"
    assert settings.local_storage_path == "wiki"
    assert settings.runtime_settings_backend == "env"
    assert settings.runtime_settings_namespace == "runtime"
    assert settings.postgres_dsn is None
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.draft_queue_name == "draft_tasks"
    assert settings.draft_llm_provider == "ollama"
    assert settings.draft_llm_model == "gemma4:e4b"
    assert settings.review_llm_provider == "ollama"
    assert settings.review_llm_model == "hermes3:8b"
    assert settings.mcp_server_host == "127.0.0.1"
    assert settings.mcp_server_port == 8000
    assert settings.mcp_server_path == "/mcp"
    assert settings.mcp_auth_enabled is False
    assert settings.mcp_auth_token is None
    assert settings.mcp_default_role is None
    assert settings.mcp_allowed_visibilities == [
        Visibility.PUBLIC,
        Visibility.INTERNAL,
    ]
    assert settings.otel_enabled is False
    assert settings.otel_exporter == "console"
    assert settings.otel_service_namespace == "waygate"


def test_runtime_settings_overrides(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_PROVIDER", "s3")
    monkeypatch.setenv("LOCAL_STORAGE_PATH", "/tmp/waygate")
    monkeypatch.setenv("RUNTIME_SETTINGS_BACKEND", "env")
    monkeypatch.setenv("RUNTIME_SETTINGS_NAMESPACE", "runtime")
    monkeypatch.setenv(
        "POSTGRES_DSN", "postgresql://waygate:waygate@localhost:5432/waygate"
    )
    monkeypatch.setenv("REDIS_URL", "redis://example:6380/4")
    monkeypatch.setenv("DRAFT_QUEUE_NAME", "compile")
    monkeypatch.setenv("DRAFT_LLM_PROVIDER", "test-provider")
    monkeypatch.setenv("DRAFT_LLM_MODEL", "draft-model")
    monkeypatch.setenv("REVIEW_LLM_PROVIDER", "review-provider")
    monkeypatch.setenv("REVIEW_LLM_MODEL", "review-model")
    monkeypatch.setenv("MCP_SERVER_HOST", "0.0.0.0")
    monkeypatch.setenv("MCP_SERVER_PORT", "9001")
    monkeypatch.setenv("MCP_SERVER_PATH", "/briefing")
    monkeypatch.setenv("MCP_AUTH_ENABLED", "true")
    monkeypatch.setenv("MCP_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("MCP_DEFAULT_ROLE", "ops_agent")
    monkeypatch.setenv("MCP_ALLOWED_VISIBILITIES", "public")
    monkeypatch.setenv("OTEL_ENABLED", "true")
    monkeypatch.setenv("OTEL_EXPORTER", "otlp")
    monkeypatch.setenv("OTEL_SERVICE_NAMESPACE", "waygate-prod")

    settings = reload_runtime_settings()

    assert settings.storage_provider == "s3"
    assert settings.local_storage_path == "/tmp/waygate"
    assert settings.runtime_settings_backend == "env"
    assert settings.runtime_settings_namespace == "runtime"
    assert (
        settings.postgres_dsn == "postgresql://waygate:waygate@localhost:5432/waygate"
    )
    assert settings.redis_url == "redis://example:6380/4"
    assert settings.draft_queue_name == "compile"
    assert settings.draft_llm_provider == "test-provider"
    assert settings.draft_llm_model == "draft-model"
    assert settings.review_llm_provider == "review-provider"
    assert settings.review_llm_model == "review-model"
    assert settings.mcp_server_host == "0.0.0.0"
    assert settings.mcp_server_port == 9001
    assert settings.mcp_server_path == "/briefing"
    assert settings.mcp_auth_enabled is True
    assert settings.mcp_auth_token == "secret-token"
    assert settings.mcp_default_role == "ops_agent"
    assert settings.mcp_allowed_visibilities == [Visibility.PUBLIC]
    assert settings.otel_enabled is True
    assert settings.otel_exporter == "otlp"
    assert settings.otel_service_namespace == "waygate-prod"


def test_runtime_settings_reload_is_stable(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://example:6380/4")
    first = reload_runtime_settings()
    second = reload_runtime_settings()

    assert first.redis_url == second.redis_url == "redis://example:6380/4"


def test_runtime_settings_can_load_postgres_overrides(monkeypatch) -> None:
    monkeypatch.setenv("RUNTIME_SETTINGS_BACKEND", "postgres")
    monkeypatch.setenv(
        "POSTGRES_DSN", "postgresql://waygate:waygate@localhost:5432/waygate"
    )
    monkeypatch.setenv("RUNTIME_SETTINGS_NAMESPACE", "runtime")
    monkeypatch.setenv("REDIS_URL", "redis://env:6379/0")

    monkeypatch.setattr(
        settings_module,
        "load_settings_namespace",
        lambda backend, postgres_dsn, namespace: {
            "redis_url": "redis://db:6379/2",
            "draft_queue_name": "db-queue",
            "mcp_allowed_visibilities": ["public"],
        },
    )

    settings = reload_runtime_settings()

    assert settings.runtime_settings_backend == "postgres"
    assert settings.redis_url == "redis://db:6379/2"
    assert settings.draft_queue_name == "db-queue"
    assert settings.mcp_allowed_visibilities == [Visibility.PUBLIC]


def test_runtime_settings_postgres_backend_requires_dsn(monkeypatch) -> None:
    monkeypatch.setenv("RUNTIME_SETTINGS_BACKEND", "postgres")
    monkeypatch.delenv("POSTGRES_DSN", raising=False)

    with pytest.raises(
        ValueError,
        match="POSTGRES_DSN must be set when RUNTIME_SETTINGS_BACKEND=postgres",
    ):
        reload_runtime_settings()
