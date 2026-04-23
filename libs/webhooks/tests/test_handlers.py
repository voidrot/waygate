from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from waygate_core.plugin import WebhookPlugin, WebhookVerificationError
from waygate_webhooks.handlers import create_webhook_router


class RejectingWebhookPlugin(WebhookPlugin):
    @property
    def name(self) -> str:
        return "rejecting"

    async def handle_webhook(self, payload: dict) -> list:
        return []

    async def verify_webhook_request(self, headers, body: bytes) -> None:
        raise WebhookVerificationError("bad signature")

    async def enrich_webhook_payload(self, payload: dict, headers) -> dict:
        return payload


class EchoWebhookPlugin(WebhookPlugin):
    @property
    def name(self) -> str:
        return "echo"

    async def handle_webhook(self, payload: dict) -> list:
        return []

    async def verify_webhook_request(self, headers, body: bytes) -> None:
        return None

    async def enrich_webhook_payload(self, payload: dict, headers) -> dict:
        return payload


def _make_test_app(monkeypatch: pytest.MonkeyPatch, plugin: WebhookPlugin) -> FastAPI:
    app_context = SimpleNamespace(
        plugins=SimpleNamespace(webhooks={plugin.name: plugin})
    )
    monkeypatch.setattr(
        "waygate_webhooks.handlers.get_app_context", lambda: app_context
    )

    app = FastAPI()
    app.include_router(create_webhook_router())
    return app


def test_handler_returns_401_when_verification_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(_make_test_app(monkeypatch, RejectingWebhookPlugin()))

    response = client.post("/rejecting", json={})

    assert response.status_code == 401
    assert response.json() == {"detail": "bad signature"}


def test_handler_returns_400_for_invalid_json_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(_make_test_app(monkeypatch, EchoWebhookPlugin()))

    response = client.post(
        "/echo",
        content=b"{",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Invalid JSON payload")
