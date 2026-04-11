from fastapi.testclient import TestClient

from waygate_api.server import app


def test_root_returns_hello_world() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
