from compiler import worker, middleware
from contextlib import contextmanager


class _FakeStorage:
    def __init__(self) -> None:
        self.audit_events = []

    def write_audit_event(self, event) -> str:
        self.audit_events.append(event)
        return f"meta/audit/{event.event_id}"


def test_execute_graph_emits_worker_and_node_audit_events(monkeypatch) -> None:
    fake_storage = _FakeStorage()
    span_calls = []
    middleware.clear_hooks()
    monkeypatch.setattr(worker, "storage", fake_storage)
    monkeypatch.setattr(middleware, "_emit_audit_event", fake_storage.write_audit_event)
    monkeypatch.setattr(worker, "configure_tracing", lambda service_name: True)

    @contextmanager
    def fake_start_span(name: str, *, tracer_name: str, attributes=None):
        span_calls.append((name, attributes or {}))

        class _FakeSpan:
            def set_attribute(self, key: str, value: object) -> None:
                span_calls.append((key, {"value": value}))

        yield _FakeSpan()

    monkeypatch.setattr(worker, "start_span", fake_start_span)

    def fake_build_graph():
        class _FakeWorkflow:
            def invoke(self, state):
                wrapped = middleware.apply_hooks(
                    "draft",
                    lambda current_state: {**current_state, "status": "completed"},
                )
                result = wrapped(state)
                assert len(fake_storage.audit_events) == 3
                assert fake_storage.audit_events[0].payload["status"] == "pending_draft"
                assert fake_storage.audit_events[1].payload["node_name"] == "draft"
                assert (
                    fake_storage.audit_events[2].payload["result_status"] == "completed"
                )
                return result

        return _FakeWorkflow()

    monkeypatch.setattr(worker, "build_graph", fake_build_graph)

    result = worker.execute_graph(
        {
            "state_version": "1",
            "trace_id": "trace-worker-1",
            "enqueued_at": "2026-04-06T12:00:00+00:00",
            "new_document_uris": ["file:///tmp/raw-1.md"],
            "raw_documents_metadata": [{"doc_id": "raw-1"}],
            "target_topic": "Topic",
            "current_draft": None,
            "qa_feedback": None,
            "staging_uri": None,
            "revision_count": 0,
            "status": "pending_draft",
        }
    )

    assert result["status"] == "completed"
    assert len(fake_storage.audit_events) == 4
    assert str(fake_storage.audit_events[0].event_type) == "compiler_worker_started"
    assert str(fake_storage.audit_events[1].event_type) == "compiler_node_started"
    assert str(fake_storage.audit_events[2].event_type) == "compiler_node_completed"
    assert str(fake_storage.audit_events[3].event_type) == "compiler_worker_completed"
    assert span_calls[0][0] == "compiler.execute_graph"
    assert span_calls[0][1]["waygate.trace_id"] == "trace-worker-1"
