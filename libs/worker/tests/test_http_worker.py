from fastapi.testclient import TestClient

from waygate_worker.http import HTTPWorkerConfig, build_http_worker_app


def test_http_worker_accepts_trigger_and_runs_background_task() -> None:
    calls: list[dict[str, object]] = []

    def runner(payload: dict[str, object]) -> dict[str, object]:
        calls.append(payload)
        return {"status": "completed"}

    app = build_http_worker_app(HTTPWorkerConfig(), runner=runner)

    with TestClient(app) as client:
        response = client.post(
            "/workflows/trigger",
            json={
                "event_type": "draft.ready",
                "source": "test",
                "document_paths": ["file://raw/example.txt"],
            },
        )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert calls == [
        {
            "event_type": "draft.ready",
            "source": "test",
            "document_paths": ["file://raw/example.txt"],
            "idempotency_key": None,
            "metadata": {},
        }
    ]


def test_http_worker_rejects_invalid_auth_token() -> None:
    app = build_http_worker_app(
        HTTPWorkerConfig(auth_token="secret-token"),
        runner=lambda payload: {"status": "completed"},
    )

    with TestClient(app) as client:
        response = client.post(
            "/workflows/trigger",
            json={
                "event_type": "draft.ready",
                "source": "test",
                "document_paths": ["file://raw/example.txt"],
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
