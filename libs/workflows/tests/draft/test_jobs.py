from waygate_workflows.draft.jobs import process_workflow_trigger


def test_process_workflow_trigger_returns_existing_document_uris() -> None:
    document_uri = "file://staging/drafts/source.md"
    result = process_workflow_trigger(
        {
            "event_type": "draft.ready",
            "source": "test-suite",
            "document_paths": [document_uri],
            "idempotency_key": "draft-123",
            "metadata": {"origin": "unit-test"},
        }
    )

    assert result["status"] == "triggered"
    assert result["request_key"]
    assert result["document_paths"] == [document_uri]
    assert result["metadata"] == {"origin": "unit-test"}


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
