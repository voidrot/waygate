import asyncio

from redis.exceptions import RedisError
from rq.exceptions import DuplicateJobError

from waygate_core.plugin import DispatchErrorKind, WorkflowTriggerMessage
from waygate_plugin_communication_rq.plugin import (
    CommunicationRQConfig,
    CommunicationRQPlugin,
)


class FakeJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id


class FakeQueue:
    def __init__(self, name: str, connection) -> None:
        self.name = name
        self.connection = connection
        self.enqueue_calls: list[dict[str, object]] = []
        self.raise_duplicate = False
        self.raise_redis_error = False

    def enqueue(self, job_function: str, **kwargs):
        if self.raise_duplicate:
            raise DuplicateJobError()
        if self.raise_redis_error:
            raise RedisError("redis unavailable")
        self.enqueue_calls.append({"job_function": job_function, **kwargs})
        job_id = kwargs.get("job_id", "rq-job-123")
        return FakeJob(job_id)


def test_submit_workflow_trigger_enqueues_rq_job(monkeypatch) -> None:
    fake_queue = FakeQueue("draft", object())

    monkeypatch.setattr(
        "waygate_plugin_communication_rq.plugin.Redis.from_url",
        lambda url: object(),
    )
    monkeypatch.setattr(
        "waygate_plugin_communication_rq.plugin.Queue",
        lambda name, connection: fake_queue,
    )

    plugin = CommunicationRQPlugin(
        CommunicationRQConfig(redis_url="redis://example", retry_max=1)
    )
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["file://wiki/raw/one.txt"],
                idempotency_key="draft-1",
            )
        )
    )

    assert result.accepted is True
    assert result.transport_message_id == "draft.ready-draft-1"
    assert fake_queue.enqueue_calls[0]["job_function"] == (
        "waygate_worker.rq.process_rq_workflow_trigger"
    )


def test_submit_workflow_trigger_returns_validation_error_for_missing_documents() -> (
    None
):
    plugin = CommunicationRQPlugin()

    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=[],
            )
        )
    )

    assert result.accepted is False
    assert result.error_kind == DispatchErrorKind.VALIDATION


def test_submit_workflow_trigger_treats_duplicate_job_as_accepted(monkeypatch) -> None:
    fake_queue = FakeQueue("draft", object())
    fake_queue.raise_duplicate = True

    monkeypatch.setattr(
        "waygate_plugin_communication_rq.plugin.Redis.from_url",
        lambda url: object(),
    )
    monkeypatch.setattr(
        "waygate_plugin_communication_rq.plugin.Queue",
        lambda name, connection: fake_queue,
    )

    plugin = CommunicationRQPlugin(CommunicationRQConfig(redis_url="redis://example"))
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["file://wiki/raw/one.txt"],
                idempotency_key="draft-1",
            )
        )
    )

    assert result.accepted is True
    assert result.transport_message_id == "draft.ready-draft-1"


def test_submit_workflow_trigger_maps_redis_errors_to_transient(monkeypatch) -> None:
    fake_queue = FakeQueue("draft", object())
    fake_queue.raise_redis_error = True

    monkeypatch.setattr(
        "waygate_plugin_communication_rq.plugin.Redis.from_url",
        lambda url: object(),
    )
    monkeypatch.setattr(
        "waygate_plugin_communication_rq.plugin.Queue",
        lambda name, connection: fake_queue,
    )

    plugin = CommunicationRQPlugin(CommunicationRQConfig(redis_url="redis://example"))
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["file://wiki/raw/one.txt"],
            )
        )
    )

    assert result.accepted is False
    assert result.error_kind == DispatchErrorKind.TRANSIENT


def test_submit_workflow_trigger_routes_ready_integrate_to_draft_queue(
    monkeypatch,
) -> None:
    fake_queue = FakeQueue("draft", object())

    monkeypatch.setattr(
        "waygate_plugin_communication_rq.plugin.Redis.from_url",
        lambda url: object(),
    )
    monkeypatch.setattr(
        "waygate_plugin_communication_rq.plugin.Queue",
        lambda name, connection: fake_queue,
    )

    plugin = CommunicationRQPlugin(
        CommunicationRQConfig(redis_url="redis://example", retry_max=1)
    )
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="ready.integrate",
                source="test",
                document_paths=["file://compiled/compiled-abc.md"],
                idempotency_key="compiled-abc",
            )
        )
    )

    assert result.accepted is True
    assert result.transport_message_id == "ready.integrate-compiled-abc"
    assert fake_queue.name == "draft"
