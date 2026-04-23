import asyncio
from types import SimpleNamespace

from waygate_worker.runtime import run_worker


def test_run_worker_uses_configured_transport(monkeypatch) -> None:
    calls: list[object] = []

    class FakeTransport:
        async def run(self, runner, *, stop_event=None) -> None:
            calls.append({"runner": runner, "stop_event": stop_event})

    context = SimpleNamespace(
        config=SimpleNamespace(
            core=SimpleNamespace(communication_plugin_name="communication-rq")
        ),
        plugins=SimpleNamespace(
            communication_workers={"communication-rq": FakeTransport()}
        ),
    )

    monkeypatch.setattr("waygate_worker.runtime.bootstrap_app", lambda: context)
    monkeypatch.setattr(
        "waygate_worker.runtime.validate_compile_llm_readiness",
        lambda: calls.append("validated"),
    )

    asyncio.run(run_worker())

    assert calls[0] == "validated"
    assert calls[1]["stop_event"] is None


def test_run_worker_allows_plugin_override(monkeypatch) -> None:
    calls: list[str] = []

    class FakeTransport:
        async def run(self, runner, *, stop_event=None) -> None:
            calls.append("run")

    context = SimpleNamespace(
        config=SimpleNamespace(
            core=SimpleNamespace(communication_plugin_name="communication-http")
        ),
        plugins=SimpleNamespace(
            communication_workers={"communication-nats": FakeTransport()}
        ),
    )

    monkeypatch.setattr("waygate_worker.runtime.bootstrap_app", lambda: context)
    monkeypatch.setattr(
        "waygate_worker.runtime.validate_compile_llm_readiness",
        lambda: None,
    )

    asyncio.run(run_worker(preferred_plugin_name="communication-nats"))

    assert calls == ["run"]
