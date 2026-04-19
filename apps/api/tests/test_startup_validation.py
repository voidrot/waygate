from types import SimpleNamespace

import pytest

from waygate_api import main
from waygate_core.plugin import CommunicationClientResolutionError


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
    monkeypatch.setattr("waygate_api.bootstrap_app", lambda: context)
    monkeypatch.setattr("waygate_api.uvicorn.run", lambda *args, **kwargs: None)

    with pytest.raises(CommunicationClientResolutionError, match="unavailable"):
        main()


def test_main_runs_when_configured_plugin_is_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _make_context("communication-http", {"communication-http": object()})
    run_calls = {"count": 0}

    monkeypatch.setattr("waygate_api.bootstrap_app", lambda: context)

    def fake_run(*args, **kwargs):
        run_calls["count"] += 1

    monkeypatch.setattr("waygate_api.uvicorn.run", fake_run)

    main()

    assert run_calls["count"] == 1
