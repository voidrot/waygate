from types import SimpleNamespace

import pytest

from waygate_draft_worker import _resolve_runtime, main
from waygate_core.plugin import LLMConfigurationError


def _make_context(redis_url: str | None = None, queue_name: str = "draft"):
    return SimpleNamespace(
        config=SimpleNamespace(
            core=SimpleNamespace(redis_dsn="redis://core"),
            communication_rq=SimpleNamespace(
                redis_url=redis_url,
                draft_queue_name=queue_name,
            ),
        )
    )


def test_resolve_runtime_prefers_plugin_redis_url() -> None:
    redis_url, queue_name = _resolve_runtime(_make_context(redis_url="redis://plugin"))

    assert redis_url == "redis://plugin"
    assert queue_name == "draft"


def test_resolve_runtime_raises_when_rq_config_missing() -> None:
    context = SimpleNamespace(
        config=SimpleNamespace(core=SimpleNamespace(redis_dsn="redis://core"))
    )

    with pytest.raises(RuntimeError, match="communication-rq configuration"):
        _resolve_runtime(context)


def test_main_builds_worker_and_starts(monkeypatch) -> None:
    context = _make_context(redis_url=None, queue_name="draft-queue")
    queue_calls: list[tuple[str, object]] = []
    worker_calls: list[dict[str, object]] = []

    class FakeWorker:
        def __init__(self, queues, connection) -> None:
            worker_calls.append({"queues": queues, "connection": connection})

        def work(self, *, with_scheduler: bool) -> None:
            worker_calls.append({"with_scheduler": with_scheduler})

    monkeypatch.setattr("waygate_draft_worker.bootstrap_app", lambda: context)
    monkeypatch.setattr(
        "waygate_draft_worker.validate_compile_llm_readiness",
        lambda: None,
    )
    monkeypatch.setattr(
        "waygate_draft_worker.Redis.from_url",
        lambda url: {"url": url},
    )
    monkeypatch.setattr(
        "waygate_draft_worker.Queue",
        lambda name, connection: queue_calls.append((name, connection)) or name,
    )
    monkeypatch.setattr("waygate_draft_worker.Worker", FakeWorker)

    main()

    assert queue_calls == [("draft-queue", {"url": "redis://core"})]
    assert worker_calls[-1] == {"with_scheduler": False}


def test_main_fails_fast_when_llm_preflight_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _make_context(redis_url=None, queue_name="draft-queue")

    monkeypatch.setattr("waygate_draft_worker.bootstrap_app", lambda: context)
    monkeypatch.setattr(
        "waygate_draft_worker.validate_compile_llm_readiness",
        lambda: (_ for _ in ()).throw(
            LLMConfigurationError("Configured LLM provider startup preflight failed")
        ),
    )
    monkeypatch.setattr(
        "waygate_draft_worker.Redis.from_url",
        lambda url: (_ for _ in ()).throw(
            AssertionError("Redis should not be reached")
        ),
    )

    with pytest.raises(LLMConfigurationError, match="startup preflight failed"):
        main()
