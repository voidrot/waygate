from waygate_core.schemas import Visibility
from waygate_core.settings import reload_runtime_settings


def test_runtime_settings_defaults(monkeypatch) -> None:
    monkeypatch.delenv("STORAGE_PROVIDER", raising=False)
    monkeypatch.delenv("LOCAL_STORAGE_PATH", raising=False)
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

    settings = reload_runtime_settings()

    assert settings.storage_provider == "local"
    assert settings.local_storage_path == "wiki"
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


def test_runtime_settings_overrides(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_PROVIDER", "s3")
    monkeypatch.setenv("LOCAL_STORAGE_PATH", "/tmp/waygate")
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

    settings = reload_runtime_settings()

    assert settings.storage_provider == "s3"
    assert settings.local_storage_path == "/tmp/waygate"
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


def test_runtime_settings_reload_is_stable(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://example:6380/4")
    first = reload_runtime_settings()
    second = reload_runtime_settings()

    assert first.redis_url == second.redis_url == "redis://example:6380/4"
