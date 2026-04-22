from types import SimpleNamespace

import pytest

from waygate_core.plugin import CommunicationClientResolutionError
from waygate_web import main


def _make_context(plugin_name: str, plugins: dict[str, object]):
    return SimpleNamespace(
        config=SimpleNamespace(
            core=SimpleNamespace(communication_plugin_name=plugin_name)
        ),
        plugins=SimpleNamespace(communication=plugins),
    )


def test_main_fails_fast_when_configured_plugin_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _make_context("missing", {"communication-http": object()})
    monkeypatch.setattr("waygate_web.bootstrap_app", lambda: context)
    monkeypatch.setattr("waygate_web.uvicorn.run", lambda *args, **kwargs: None)

    with pytest.raises(CommunicationClientResolutionError, match="unavailable"):
        main()


def test_main_runs_when_configured_plugin_is_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _make_context("communication-http", {"communication-http": object()})
    run_calls: dict[str, object] = {}

    monkeypatch.setattr("waygate_web.bootstrap_app", lambda: context)
    monkeypatch.setenv("WAYGATE_WEB__HOST", "127.0.0.1")
    monkeypatch.setenv("WAYGATE_WEB__PORT", "9090")

    def fake_run(*args, **kwargs):
        run_calls.update(kwargs)

    monkeypatch.setattr("waygate_web.uvicorn.run", fake_run)

    main()

    assert run_calls["host"] == "127.0.0.1"
    assert run_calls["port"] == 9090
