from waygate_api.routes.webhooks.router import _build_openapi_extra
from waygate_plugin_webhook_generic.plugin import GenericWebhookPlugin


def test_build_openapi_extra_includes_generic_webhook_payload_schema() -> None:
    plugin = GenericWebhookPlugin()

    extra = _build_openapi_extra(plugin)

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
