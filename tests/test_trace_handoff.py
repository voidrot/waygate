from contextlib import contextmanager
from datetime import datetime, timezone

import pytest

from compiler import middleware, worker
from receiver.services import trigger
from waygate_core.plugin_base import RawDocument


class _SharedStorage:
    def __init__(self) -> None:
        self.saved_documents: list[RawDocument] = []
        self.audit_events = []

    def write_raw_documents(self, documents: list[RawDocument]) -> list[str]:
        self.saved_documents.extend(documents)
        return [f"file:///tmp/raw/{document.doc_id}.md" for document in documents]

    def write_audit_event(self, event) -> str:
        self.audit_events.append(event)
        return f"meta/audit/{event.event_id}"


class _FakeJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id


class _FakeQueue:
    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return _FakeJob("job-trace-handoff-1")


@pytest.mark.anyio
async def test_trace_id_survives_receiver_enqueue_into_compiler_worker(
    monkeypatch,
) -> None:
    shared_storage = _SharedStorage()
    fake_queue = _FakeQueue()
    span_calls = []

    middleware.clear_hooks()
    monkeypatch.setattr(trigger, "storage", shared_storage)
    monkeypatch.setattr(trigger, "draft_queue", fake_queue)
    monkeypatch.setattr(worker, "storage", shared_storage)
    monkeypatch.setattr(middleware, "_emit_audit_event", shared_storage.write_audit_event)
    monkeypatch.setattr(worker, "configure_tracing", lambda _service_name: None)

    @contextmanager
    def fake_start_span(name: str, *, tracer_name: str, attributes=None):
        span_calls.append((name, attributes or {}))

        class _FakeSpan:
            def set_attribute(self, key: str, value: object) -> None:
                span_calls.append((key, {"value": value}))

        yield _FakeSpan()

    monkeypatch.setattr(trigger, "start_span", fake_start_span)
    monkeypatch.setattr(worker, "start_span", fake_start_span)
    monkeypatch.setattr(middleware, "start_span", fake_start_span)

    def fake_build_graph():
        class _FakeWorkflow:
            def invoke(self, state):
                wrapped = middleware.apply_hooks(
                    "draft",
                    lambda current_state: {**current_state, "status": "completed"},
                )
                return wrapped(state)

        return _FakeWorkflow()

    monkeypatch.setattr(worker, "build_graph", fake_build_graph)

    documents = [
        RawDocument(
            source_type="github",
            source_id="issue/1",
            timestamp=datetime(2026, 4, 8, tzinfo=timezone.utc),
            content="hello",
            tags=["ops"],
        )
    ]

    await trigger.save_and_trigger_langgraph_async(documents)

    assert len(fake_queue.calls) == 1
    initial_state = fake_queue.calls[0][0][1]
    receiver_event = shared_storage.audit_events[0]
    assert receiver_event.trace_id == initial_state["trace_id"]

    result = worker.execute_graph(initial_state)

    assert result["status"] == "completed"
    assert [str(event.event_type) for event in shared_storage.audit_events] == [
        "receiver_enqueued",
        "compiler_worker_started",
        "compiler_node_started",
        "compiler_node_completed",
        "compiler_worker_completed",
    ]
    assert all(
        event.trace_id == initial_state["trace_id"]
        for event in shared_storage.audit_events
    )

    named_spans = {
        name: attributes
        for name, attributes in span_calls
        if not name.startswith("waygate.")
    }
    assert named_spans["receiver.enqueue_documents"]["waygate.trace_id"] == initial_state[
        "trace_id"
    ]
    assert named_spans["compiler.execute_graph"]["waygate.trace_id"] == initial_state[
        "trace_id"
    ]
    assert named_spans["compiler.node.draft"]["waygate.trace_id"] == initial_state[
        "trace_id"
    ]