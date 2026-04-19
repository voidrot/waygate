from waygate_core.plugin import LLMConfigurationError
from waygate_workflows.draft.jobs import process_workflow_trigger


def test_process_workflow_trigger_returns_completed_result(monkeypatch) -> None:
    document_uri = "file://staging/drafts/source.md"

    monkeypatch.setattr(
        "waygate_workflows.router._invoke_compile_workflow",
        lambda message: (
            "compile:draft-123",
            {
                "source_set_key": "hash-abc",
                "published_document_uri": "file://published/hash-abc.md",
                "published_document_id": "hash-abc",
            },
        ),
    )

    result = process_workflow_trigger(
        {
            "event_type": "draft.ready",
            "source": "test-suite",
            "document_paths": [document_uri],
            "idempotency_key": "draft-123",
            "metadata": {"origin": "unit-test"},
        }
    )

    assert result["status"] == "completed"
    assert result["request_key"] == "compile:draft-123"
    assert result["document_paths"] == [document_uri]
    assert result["metadata"] == {"origin": "unit-test"}
    assert result["published_document_uri"] == "file://published/hash-abc.md"
    assert result["published_document_id"] == "hash-abc"


def test_process_workflow_trigger_returns_human_review(monkeypatch) -> None:
    monkeypatch.setattr(
        "waygate_workflows.router._invoke_compile_workflow",
        lambda message: (
            "compile:draft-789",
            {
                "source_set_key": "hash-review",
                "human_review_record_uri": "file://review/hash-review.json",
                "__interrupt__": [{"value": {"type": "compile_human_review"}}],
            },
        ),
    )

    result = process_workflow_trigger(
        {
            "event_type": "draft.ready",
            "source": "test-suite",
            "document_paths": ["file://raw/source.md"],
            "metadata": {},
        }
    )

    assert result["status"] == "human_review"
    assert result["request_key"] == "compile:draft-789"
    assert result["human_review_record_uri"] == "file://review/hash-review.json"
    assert result["source_set_key"] == "hash-review"
    assert result["interrupts"] == [{"value": {"type": "compile_human_review"}}]


def test_process_workflow_trigger_ignores_unknown_event_type() -> None:
    result = process_workflow_trigger(
        {
            "event_type": "unknown.event",
            "source": "test-suite",
            "document_paths": [],
            "metadata": {},
        }
    )

    assert result["status"] == "ignored"
    assert result["event_type"] == "unknown.event"


def test_process_workflow_trigger_returns_failed_config_result(monkeypatch) -> None:
    def raise_config_error(message) -> tuple[str, dict[str, object]]:
        raise LLMConfigurationError(
            "Unsupported LLM options for provider OllamaProvider"
        )

    monkeypatch.setattr(
        "waygate_workflows.router._invoke_compile_workflow",
        raise_config_error,
    )

    result = process_workflow_trigger(
        {
            "event_type": "draft.ready",
            "source": "test-suite",
            "document_paths": ["file://raw/source.md"],
            "idempotency_key": "draft-config-123",
            "metadata": {"origin": "unit-test"},
        }
    )

    assert result["status"] == "failed"
    assert result["error_kind"] == "config"
    assert result["request_key"] == "compile:draft-config-123"
    assert result["event_type"] == "draft.ready"
    assert result["document_paths"] == ["file://raw/source.md"]
    assert result["metadata"] == {"origin": "unit-test"}
    assert "Unsupported LLM options" in result["detail"]
