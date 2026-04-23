from waygate_worker_app import main


def test_main_runs_shared_worker_without_override(monkeypatch) -> None:
    calls = []

    async def fake_run_worker() -> None:
        calls.append("run")

    monkeypatch.setattr("waygate_worker_app.run_worker", fake_run_worker)

    main()

    assert calls == ["run"]
