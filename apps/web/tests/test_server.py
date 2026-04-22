from fastapi.testclient import TestClient

from waygate_web.server import app


def test_root_dashboard_renders() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "WayGate Control Plane" in response.text
    assert "Runtime summary" in response.text


def test_parent_openapi_includes_mounted_webhook_paths() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/webhooks/generic-webhook" in schema["paths"]
