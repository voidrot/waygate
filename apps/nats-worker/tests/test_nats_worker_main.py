from waygate_nats_worker import main


def test_main_runs_worker(monkeypatch) -> None:
    calls = []

    async def fake_run_worker() -> None:
        calls.append("run")

    monkeypatch.setattr("waygate_nats_worker.run_nats_worker", fake_run_worker)

    main()

    assert calls == ["run"]
