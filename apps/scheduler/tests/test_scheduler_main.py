import asyncio
from types import SimpleNamespace

import pytest

from waygate_scheduler import (
    _build_cron_job,
    _install_signal_handlers,
    _register_cron_jobs,
    _resolve_communication_client,
    main,
    _run_cron_plugin,
)
from waygate_core.plugin import (
    CommunicationClientResolutionError,
    WorkflowDispatchResult,
)


class FakeCronPlugin:
    def __init__(self, name: str = "CronA", schedule: str = "* * * * *") -> None:
        self._name = name
        self._schedule = schedule
        self.run_calls = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def schedule(self) -> str:
        return self._schedule

    async def run(self, payload: dict) -> None:
        self.run_calls.append(payload)


class FakeCommunicationClient:
    def __init__(self) -> None:
        self.messages = []

    async def submit_workflow_trigger(self, message):
        self.messages.append(message)
        return WorkflowDispatchResult(accepted=True, transport_message_id="cron-1")


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs: list[dict[str, object]] = []

    def add_job(self, func, trigger, **kwargs) -> None:
        self.jobs.append({"func": func, "trigger": trigger, **kwargs})


class FakeLoop:
    def __init__(self) -> None:
        self.handlers: list[tuple[object, object, tuple[object, ...]]] = []

    def add_signal_handler(self, sig, callback, *args) -> None:
        self.handlers.append((sig, callback, args))


def _make_context(
    preferred_name: str,
    cron_plugins: dict[str, object],
    communication: dict[str, object],
):
    return SimpleNamespace(
        config=SimpleNamespace(
            core=SimpleNamespace(communication_plugin_name=preferred_name)
        ),
        plugins=SimpleNamespace(cron=cron_plugins, communication=communication),
    )


def test_resolve_communication_client_returns_preferred() -> None:
    preferred = FakeCommunicationClient()
    fallback = FakeCommunicationClient()
    context = _make_context(
        "preferred", {}, {"preferred": preferred, "fallback": fallback}
    )

    resolved = _resolve_communication_client(context)

    assert resolved is preferred


def test_resolve_communication_client_raises_when_unavailable() -> None:
    context = _make_context("preferred", {}, {})

    with pytest.raises(CommunicationClientResolutionError, match="No communication"):
        _resolve_communication_client(context)


def test_run_cron_plugin_runs_plugin_and_submits_message() -> None:
    cron_plugin = FakeCronPlugin(name="DailyDigest", schedule="0 0 * * *")
    communication_client = FakeCommunicationClient()

    asyncio.run(_run_cron_plugin(cron_plugin, communication_client))

    assert len(cron_plugin.run_calls) == 1
    assert cron_plugin.run_calls[0] == {
        "source": "waygate-scheduler",
        "mode": "scheduled",
    }
    assert len(communication_client.messages) == 1
    message = communication_client.messages[0]
    assert message.event_type == "cron.tick"
    assert message.source == "waygate-scheduler.cron.DailyDigest"
    assert message.metadata == {"schedule": "0 0 * * *"}


def test_register_cron_jobs_adds_one_job_per_plugin() -> None:
    cron_plugin = FakeCronPlugin(name="Nightly", schedule="15 3 * * *")
    communication_client = FakeCommunicationClient()
    context = _make_context(
        "communication-http",
        {"nightly": cron_plugin},
        {"communication-http": communication_client},
    )
    scheduler = FakeScheduler()

    _register_cron_jobs(scheduler, context, communication_client)

    assert len(scheduler.jobs) == 1
    job = scheduler.jobs[0]
    assert job["id"] == "cron:nightly"
    assert job["name"] == "cron:Nightly"
    assert job["replace_existing"] is True
    assert job["coalesce"] is True
    assert job["max_instances"] == 1

    asyncio.run(job["func"]())
    assert len(communication_client.messages) == 1


def test_build_cron_job_returns_awaitable_job() -> None:
    cron_plugin = FakeCronPlugin(name="Nightly")
    communication_client = FakeCommunicationClient()

    job = _build_cron_job(cron_plugin, communication_client)
    asyncio.run(job())

    assert len(cron_plugin.run_calls) == 1
    assert len(communication_client.messages) == 1


def test_main_fails_fast_when_configured_plugin_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cron_plugin = FakeCronPlugin(name="Nightly")
    context = _make_context(
        "missing",
        {"nightly": cron_plugin},
        {"communication-http": object()},
    )

    async def fake_run_scheduler() -> None:
        _resolve_communication_client(context)

    monkeypatch.setattr("waygate_scheduler._run_scheduler", fake_run_scheduler)

    with pytest.raises(CommunicationClientResolutionError, match="unavailable"):
        main()


def test_install_signal_handlers_registers_sigint_and_sigterm() -> None:
    fake_loop = FakeLoop()
    stop_event = asyncio.Event()

    _install_signal_handlers(fake_loop, stop_event)

    registered = {handler[0].name for handler in fake_loop.handlers}
    assert registered == {"SIGINT", "SIGTERM"}


def test_install_signal_handlers_callback_sets_stop_event() -> None:
    fake_loop = FakeLoop()
    stop_event = asyncio.Event()

    _install_signal_handlers(fake_loop, stop_event)

    assert stop_event.is_set() is False
    _, callback, args = fake_loop.handlers[0]
    callback(*args)
    assert stop_event.is_set() is True
