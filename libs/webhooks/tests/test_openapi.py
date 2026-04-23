from waygate_plugin_webhook_agent_session.plugin import AgentSessionWebhookPlugin
from waygate_plugin_webhook_generic.plugin import GenericWebhookPlugin

from waygate_webhooks.app import create_webhook_app
from waygate_webhooks.handlers import create_webhook_router
from waygate_webhooks.openapi import build_webhook_openapi_extra


def test_build_openapi_extra_includes_generic_webhook_payload_schema() -> None:
    plugin = GenericWebhookPlugin()

    extra = build_webhook_openapi_extra(plugin)

    assert extra is not None
    request_body = extra["requestBody"]
    assert request_body["required"] is True

    schema = request_body["content"]["application/json"]["schema"]
    assert "$defs" not in schema
    assert schema["title"] == "GenericWebhookPayload"
    assert (
        schema["properties"]["metadata"]["$ref"]
        == "#/components/schemas/GenericWebhookPayloadMetadata"
    )
    assert (
        schema["properties"]["documents"]["items"]["$ref"]
        == "#/components/schemas/GenericWebhookPayloadDocument"
    )


def test_build_openapi_extra_includes_agent_session_payload_schema() -> None:
    plugin = AgentSessionWebhookPlugin()

    extra = build_webhook_openapi_extra(plugin)

    assert extra is not None
    schema = extra["requestBody"]["content"]["application/json"]["schema"]
    assert "$defs" not in schema
    assert schema["title"] == "AgentSessionWebhookPayload"
    assert (
        schema["properties"]["session"]["$ref"] == "#/components/schemas/AgentSession"
    )


def test_webhook_router_registers_known_routes() -> None:
    router = create_webhook_router()

    paths = {
        path
        for route in router.routes
        if (path := getattr(route, "path", None)) is not None
    }

    assert "/agent-session" in paths
    assert "/generic-webhook" in paths


def test_create_webhook_app_openapi_includes_paths_and_component_schemas() -> None:
    app = create_webhook_app()

    schema = app.openapi()

    assert "/agent-session" in schema["paths"]
    assert "/generic-webhook" in schema["paths"]
    assert "AgentSessionWebhookPayload" in schema["components"]["schemas"]
    assert "GenericWebhookPayload" in schema["components"]["schemas"]
