import asyncio
import logging

import pytest

from waygate_core.plugin_base import IngestionPlugin


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
