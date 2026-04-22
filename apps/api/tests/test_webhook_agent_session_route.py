from waygate_api.routes.webhooks.router import _build_openapi_extra, webhook_router
from waygate_plugin_webhook_agent_session.plugin import AgentSessionWebhookPlugin


def test_build_openapi_extra_includes_agent_session_payload_schema() -> None:
    plugin = AgentSessionWebhookPlugin()

    extra = _build_openapi_extra(plugin)

    assert extra is not None
    schema = extra["requestBody"]["content"]["application/json"]["schema"]
    assert "$defs" not in schema
    assert schema["title"] == "AgentSessionWebhookPayload"
    assert (
        schema["properties"]["session"]["$ref"] == "#/components/schemas/AgentSession"
    )


def test_webhook_router_registers_agent_session_route() -> None:
    paths = {
        path
        for route in webhook_router.routes
        if (path := getattr(route, "path", None)) is not None
    }

    assert "/webhooks/agent-session" in paths
