import asyncio
from contextlib import contextmanager
import logging
from datetime import datetime, timezone

import pytest

from waygate_core.plugin_base import IngestionPlugin, RawDocument


class _PollingNotImplementedPlugin(IngestionPlugin):
    @property
    def plugin_name(self) -> str:
        return "polling_not_implemented"

    def poll(self, since_timestamp=None):
        raise NotImplementedError()


class _CronPlugin(IngestionPlugin):
    def __init__(self, name: str, cron_schedule: dict | None) -> None:
        self._name = name
        self._cron_schedule = cron_schedule or {}

    @property
    def plugin_name(self) -> str:
        return self._name

    @property
    def cron_schedule(self) -> dict:
        return self._cron_schedule


class _PassiveListenerPlugin(IngestionPlugin):
    @property
    def plugin_name(self) -> str:
        return "passive_listener"


class _ActiveListenerPlugin(IngestionPlugin):
    def __init__(self) -> None:
        self.listen_called = False

    @property
    def plugin_name(self) -> str:
        return "active_listener"

    async def listen(self, on_data_callback):
        self.listen_called = True
        await on_data_callback([])


class _PollingPlugin(IngestionPlugin):
    def __init__(self, docs: list[RawDocument]) -> None:
        self.docs = docs
        self.last_since_timestamp = None

    @property
    def plugin_name(self) -> str:
        return "polling_plugin"

    def poll(self, since_timestamp=None):
        self.last_since_timestamp = since_timestamp
        return self.docs


@pytest.mark.anyio
async def test_poll_plugin_job_handles_not_implemented(monkeypatch, caplog) -> None:
    from receiver.core import scheduler as scheduler_module

    plugin = _PollingNotImplementedPlugin()
    monkeypatch.setattr(scheduler_module.registry, "get", lambda _name: plugin)

    callback_called = False

    async def _fake_save(_documents):
        nonlocal callback_called
        callback_called = True

    monkeypatch.setattr(
        scheduler_module,
        "save_and_trigger_langgraph_async",
        _fake_save,
    )

    with caplog.at_level(logging.WARNING):
        await scheduler_module.poll_plugin_job("polling_not_implemented")

    assert not callback_called
    assert "does not implement polling" in caplog.text


@pytest.mark.anyio
async def test_poll_plugin_job_uses_and_updates_checkpoint(monkeypatch) -> None:
    from receiver.core import scheduler as scheduler_module

    current_checkpoint = datetime(2026, 4, 6, 12, 0, tzinfo=timezone.utc)
    newer_doc_time = datetime(2026, 4, 6, 12, 30, tzinfo=timezone.utc)

    plugin = _PollingPlugin(
        docs=[
            RawDocument(
                source_type="github",
                source_id="issue/1",
                timestamp=newer_doc_time,
                content="payload",
            )
        ]
    )

    monkeypatch.setattr(scheduler_module.registry, "get", lambda _name: plugin)
    monkeypatch.setattr(
        scheduler_module,
        "get_poll_checkpoint",
        lambda _plugin_name: current_checkpoint,
    )

    observed_updates: list[datetime] = []
    span_calls = []
    monkeypatch.setattr(
        scheduler_module,
        "set_poll_checkpoint",
        lambda _plugin_name, checkpoint: observed_updates.append(checkpoint),
    )

    @contextmanager
    def fake_start_span(name: str, *, tracer_name: str, attributes=None):
        span_calls.append((name, attributes or {}))

        class _FakeSpan:
            def set_attribute(self, key: str, value: object) -> None:
                span_calls.append((key, {"value": value}))

        yield _FakeSpan()

    monkeypatch.setattr(scheduler_module, "start_span", fake_start_span)

    async def _fake_save(_documents):
        return None

    monkeypatch.setattr(
        scheduler_module, "save_and_trigger_langgraph_async", _fake_save
    )

    await scheduler_module.poll_plugin_job("polling_plugin")

    assert plugin.last_since_timestamp == current_checkpoint
    assert observed_updates == [newer_doc_time]
    assert span_calls[0][0] == "receiver.poll_plugin"
    assert span_calls[0][1]["waygate.plugin_name"] == "polling_plugin"


@pytest.mark.anyio
async def test_poll_plugin_job_does_not_advance_checkpoint_on_handoff_error(
    monkeypatch,
) -> None:
    from receiver.core import scheduler as scheduler_module

    plugin = _PollingPlugin(
        docs=[
            RawDocument(
                source_type="github",
                source_id="issue/1",
                timestamp=datetime(2026, 4, 6, 13, 0, tzinfo=timezone.utc),
                content="payload",
            )
        ]
    )

    monkeypatch.setattr(scheduler_module.registry, "get", lambda _name: plugin)
    monkeypatch.setattr(
        scheduler_module, "get_poll_checkpoint", lambda _plugin_name: None
    )

    checkpoint_advanced = False

    def _fake_set_checkpoint(_plugin_name, _checkpoint):
        nonlocal checkpoint_advanced
        checkpoint_advanced = True

    monkeypatch.setattr(scheduler_module, "set_poll_checkpoint", _fake_set_checkpoint)

    async def _failing_save(_documents):
        raise RuntimeError("handoff failed")

    monkeypatch.setattr(
        scheduler_module, "save_and_trigger_langgraph_async", _failing_save
    )

    await scheduler_module.poll_plugin_job("polling_plugin")

    assert checkpoint_advanced is False


def test_setup_scheduler_only_registers_plugins_with_cron(monkeypatch) -> None:
    from receiver.core import scheduler as scheduler_module

    plugins = {
        "cron_enabled": _CronPlugin("cron_enabled", {"minute": "*/5"}),
        "cron_disabled": _CronPlugin("cron_disabled", {}),
    }
    monkeypatch.setattr(scheduler_module.registry, "get_all", lambda: plugins)

    calls: list[dict] = []

    def _fake_add_job(func, trigger, **kwargs):
        calls.append({"func": func, "trigger": trigger, "kwargs": kwargs})

    monkeypatch.setattr(scheduler_module.scheduler, "add_job", _fake_add_job)

    scheduler_module.setup_scheduler()

    assert len(calls) == 1
    call = calls[0]
    assert call["func"] is scheduler_module.poll_plugin_job
    assert call["trigger"] == "cron"
    assert call["kwargs"]["args"] == ["cron_enabled"]
    assert call["kwargs"]["id"] == "poll_cron_enabled"


@pytest.mark.anyio
async def test_lifespan_starts_only_overridden_listeners(monkeypatch) -> None:
    from receiver import app as app_module

    active = _ActiveListenerPlugin()
    passive = _PassiveListenerPlugin()
    configured_services = []

    monkeypatch.setattr(app_module.registry, "discover_and_register", lambda: None)
    monkeypatch.setattr(
        app_module.registry,
        "get_all",
        lambda: {
            "passive_listener": passive,
            "active_listener": active,
        },
    )

    monkeypatch.setattr(app_module, "setup_scheduler", lambda: None)
    monkeypatch.setattr(
        app_module,
        "configure_tracing",
        lambda service_name: configured_services.append(service_name),
    )

    started = False
    shutdown = False

    def _start() -> None:
        nonlocal started
        started = True

    def _shutdown() -> None:
        nonlocal shutdown
        shutdown = True

    monkeypatch.setattr(app_module.scheduler, "start", _start)
    monkeypatch.setattr(app_module.scheduler, "shutdown", _shutdown)

    async def _fake_save(_documents):
        return None

    monkeypatch.setattr(app_module, "save_and_trigger_langgraph_async", _fake_save)

    created_tasks = []
    original_create_task = asyncio.create_task

    def _tracking_create_task(coro):
        task = original_create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(app_module.asyncio, "create_task", _tracking_create_task)

    async with app_module.lifespan(app_module.app):
        await asyncio.sleep(0)

    assert started
    assert shutdown
    assert active.listen_called
    assert len(created_tasks) == 1
    assert configured_services == ["waygate-receiver"]
