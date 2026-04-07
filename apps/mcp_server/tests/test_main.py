import importlib


main_module = importlib.import_module("mcp_server.main")


def test_main_runs_uvicorn_with_runtime_settings(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class SettingsStub:
        mcp_server_host = "0.0.0.0"
        mcp_server_port = 9100

    monkeypatch.setattr(main_module, "reload_runtime_settings", lambda: SettingsStub())

    def fake_run(app: str, host: str, port: int, reload: bool) -> None:
        captured["app"] = app
        captured["host"] = host
        captured["port"] = port
        captured["reload"] = reload

    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)

    main_module.main(["--reload"])

    assert captured == {
        "app": "mcp_server.server:app",
        "host": "0.0.0.0",
        "port": 9100,
        "reload": True,
    }


def test_main_runs_without_reload_by_default(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class SettingsStub:
        mcp_server_host = "127.0.0.1"
        mcp_server_port = 8000

    monkeypatch.setattr(main_module, "reload_runtime_settings", lambda: SettingsStub())

    def fake_run(app: str, host: str, port: int, reload: bool) -> None:
        captured["reload"] = reload

    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)

    main_module.main([])

    assert captured["reload"] is False
