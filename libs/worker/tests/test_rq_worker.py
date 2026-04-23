from waygate_worker.rq import RQWorkerConfig, process_rq_workflow_trigger, run_rq_worker


def test_process_rq_workflow_trigger_forwards_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "waygate_worker.rq.process_workflow_trigger",
        lambda payload: {"status": "completed", "payload": payload},
    )

    result = process_rq_workflow_trigger({"event_type": "draft.ready"})

    assert result == {
        "status": "completed",
        "payload": {"event_type": "draft.ready"},
    }


def test_run_rq_worker_builds_worker_with_both_queue_names(monkeypatch) -> None:
    queue_calls: list[tuple[str, object]] = []
    worker_calls: list[dict[str, object]] = []

    class FakeWorker:
        def __init__(self, queues, connection) -> None:
            worker_calls.append({"queues": queues, "connection": connection})

        def work(self, *, with_scheduler: bool) -> None:
            worker_calls.append({"with_scheduler": with_scheduler})

    monkeypatch.setattr(
        "waygate_worker.rq.Redis.from_url",
        lambda url: {"url": url},
    )
    monkeypatch.setattr(
        "waygate_worker.rq.Queue",
        lambda name, connection: queue_calls.append((name, connection)) or name,
    )
    monkeypatch.setattr("waygate_worker.rq.Worker", FakeWorker)

    run_rq_worker(
        RQWorkerConfig(
            redis_url="redis://core",
            draft_queue_name="draft",
            cron_queue_name="cron",
        )
    )

    assert queue_calls == [
        ("draft", {"url": "redis://core"}),
        ("cron", {"url": "redis://core"}),
    ]
    assert worker_calls[-1] == {"with_scheduler": False}
