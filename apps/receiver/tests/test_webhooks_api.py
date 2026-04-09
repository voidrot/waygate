import json

from fastapi.testclient import TestClient

from receiver.api import webhooks
from receiver.app import app
from waygate_core.plugin_base import WebhookVerificationError


class _FakePlugin:
    def __init__(self) -> None:
        self.verified: list[tuple[dict[str, str], bytes]] = []
        self.handled_payloads: list[object] = []

    def verify_webhook_request(self, headers, body: bytes) -> None:
        self.verified.append((dict(headers), body))

    def prepare_webhook_payload(self, payload, headers):
        if isinstance(payload, dict):
            enriched = dict(payload)
            enriched["prepared"] = headers.get("x-test-header")
            return enriched
        return payload

    def handle_webhook(self, payload):
        self.handled_payloads.append(payload)
        return []


def test_handle_webhook_verifies_and_prepares_payload(monkeypatch) -> None:
    plugin = _FakePlugin()
    monkeypatch.setattr(webhooks.registry, "get", lambda _name: plugin)

    client = TestClient(app)
    response = client.post(
        "/webhooks/test",
        json={"hello": "world"},
        headers={"x-test-header": "ok"},
    )

    assert response.status_code == 200
    assert len(plugin.verified) == 1
    assert plugin.handled_payloads == [{"hello": "world", "prepared": "ok"}]


def test_handle_webhook_rejects_invalid_json(monkeypatch) -> None:
    plugin = _FakePlugin()
    monkeypatch.setattr(webhooks.registry, "get", lambda _name: plugin)

    client = TestClient(app)
    response = client.post(
        "/webhooks/test",
        content=b"{not-json",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Invalid JSON payload")


def test_handle_webhook_rejects_verification_failures(monkeypatch) -> None:
    class _RejectingPlugin(_FakePlugin):
        def verify_webhook_request(self, headers, body: bytes) -> None:
            raise WebhookVerificationError("bad signature")

    monkeypatch.setattr(webhooks.registry, "get", lambda _name: _RejectingPlugin())

    client = TestClient(app)
    response = client.post("/webhooks/test", json={"hello": "world"})

    assert response.status_code == 401
    assert response.json() == {"detail": "bad signature"}