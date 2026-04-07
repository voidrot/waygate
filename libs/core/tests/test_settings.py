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

    settings = reload_runtime_settings()

    assert settings.storage_provider == "local"
    assert settings.local_storage_path == "wiki"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.draft_queue_name == "draft_tasks"
    assert settings.draft_llm_provider == "ollama"
    assert settings.draft_llm_model == "gemma4:e4b"
    assert settings.review_llm_provider == "ollama"
    assert settings.review_llm_model == "hermes3:8b"


def test_runtime_settings_overrides(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_PROVIDER", "s3")
    monkeypatch.setenv("LOCAL_STORAGE_PATH", "/tmp/waygate")
    monkeypatch.setenv("REDIS_URL", "redis://example:6380/4")
    monkeypatch.setenv("DRAFT_QUEUE_NAME", "compile")
    monkeypatch.setenv("DRAFT_LLM_PROVIDER", "test-provider")
    monkeypatch.setenv("DRAFT_LLM_MODEL", "draft-model")
    monkeypatch.setenv("REVIEW_LLM_PROVIDER", "review-provider")
    monkeypatch.setenv("REVIEW_LLM_MODEL", "review-model")

    settings = reload_runtime_settings()

    assert settings.storage_provider == "s3"
    assert settings.local_storage_path == "/tmp/waygate"
    assert settings.redis_url == "redis://example:6380/4"
    assert settings.draft_queue_name == "compile"
    assert settings.draft_llm_provider == "test-provider"
    assert settings.draft_llm_model == "draft-model"
    assert settings.review_llm_provider == "review-provider"
    assert settings.review_llm_model == "review-model"


def test_runtime_settings_reload_is_stable(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://example:6380/4")
    first = reload_runtime_settings()
    second = reload_runtime_settings()

    assert first.redis_url == second.redis_url == "redis://example:6380/4"
