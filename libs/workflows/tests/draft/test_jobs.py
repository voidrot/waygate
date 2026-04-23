from waygate_core.plugin import LLMConfigurationError
from waygate_core.plugin import WorkflowDispatchResult
from waygate_workflows.draft.jobs import process_workflow_trigger


class _RecordingLogger:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def debug(self, event: str, **kwargs: object) -> None:
        self.records.append({"level": "debug", "event": event, **kwargs})

    def info(self, event: str, **kwargs: object) -> None:
        self.records.append({"level": "info", "event": event, **kwargs})

    def warning(self, event: str, **kwargs: object) -> None:
        self.records.append({"level": "warning", "event": event, **kwargs})

    def error(self, event: str, **kwargs: object) -> None:
        self.records.append({"level": "error", "event": event, **kwargs})

    def has_event(self, level: str, event: str) -> bool:
        return any(
            record["level"] == level and record["event"] == event
            for record in self.records
        )


def test_process_workflow_trigger_returns_completed_result(monkeypatch) -> None:
    document_uri = "file://staging/drafts/source.md"
    logger = _RecordingLogger()

    monkeypatch.setattr("waygate_workflows.router.logger", logger)

    monkeypatch.setattr(
        "waygate_workflows.router._invoke_compile_workflow",
        lambda message: (
            "compile:draft-123",
            {
                "source_set_key": "hash-abc",
                "compiled_document_uri": "file://compiled/compiled-abc.md",
                "compiled_document_id": "compiled-abc",
                "compiled_document_hash": "compiled-abc",
            },
        ),
    )
    monkeypatch.setattr(
        "waygate_workflows.router._dispatch_integration_trigger",
        lambda parent_message, result: WorkflowDispatchResult(
            accepted=True,
            transport_message_id="ready.integrate-compiled-abc",
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
    assert result["compiled_document_uri"] == "file://compiled/compiled-abc.md"
    assert result["compiled_document_id"] == "compiled-abc"
    assert result["compiled_document_hash"] == "compiled-abc"
    assert logger.has_event("info", "Received workflow trigger")
    assert logger.has_event("info", "Processing draft.ready workflow trigger")
    assert logger.has_event("info", "Compile workflow completed successfully")


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


def test_process_workflow_trigger_ignores_unknown_event_type(monkeypatch) -> None:
    logger = _RecordingLogger()

    monkeypatch.setattr("waygate_workflows.router.logger", logger)
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
    assert logger.has_event("warning", "Ignoring unsupported workflow trigger event")


def test_process_workflow_trigger_ignores_ready_integrate_until_implemented() -> None:
    result = process_workflow_trigger(
        {
            "event_type": "ready.integrate",
            "source": "test-suite",
            "document_paths": ["file://compiled/compiled-abc.md"],
            "metadata": {"compiled_document_id": "compiled-abc"},
        }
    )

    assert result["status"] == "ignored"
    assert result["event_type"] == "ready.integrate"


def test_process_workflow_trigger_returns_failed_config_result(monkeypatch) -> None:
    logger = _RecordingLogger()

    monkeypatch.setattr("waygate_workflows.router.logger", logger)

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
    assert logger.has_event("error", "Compile workflow configuration failed")


def test_process_workflow_trigger_rejects_empty_draft_ready(monkeypatch) -> None:
    invoked = {"called": False}
    logger = _RecordingLogger()

    monkeypatch.setattr("waygate_workflows.router.logger", logger)

    def fail_if_called(message) -> tuple[str, dict[str, object]]:
        invoked["called"] = True
        raise AssertionError("compile workflow should not be invoked")

    monkeypatch.setattr(
        "waygate_workflows.router._invoke_compile_workflow",
        fail_if_called,
    )

    result = process_workflow_trigger(
        {
            "event_type": "draft.ready",
            "source": "test-suite",
            "document_paths": [],
            "idempotency_key": "draft-empty-123",
            "metadata": {"origin": "unit-test"},
        }
    )

    assert invoked["called"] is False
    assert result["status"] == "failed"
    assert result["error_kind"] == "validation"
    assert result["request_key"] == "compile:draft-empty-123"
    assert result["event_type"] == "draft.ready"
    assert result["document_paths"] == []
    assert result["metadata"] == {"origin": "unit-test"}
    assert "at least one document path" in result["detail"]
    assert logger.has_event(
        "error", "Rejecting draft.ready workflow trigger with no documents"
    )
