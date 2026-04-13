from fastapi.testclient import TestClient

from waygate_api.server import app


def test_root_returns_hello_world() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_openapi_includes_generic_webhook_route() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/webhooks/generic-webhook" in schema["paths"]
