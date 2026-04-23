"""OpenAPI helpers for the mountable webhook application."""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from waygate_core import get_app_context
from waygate_core.plugin import WebhookPlugin


def build_webhook_openapi_extra(plugin: WebhookPlugin) -> dict[str, Any] | None:
    """Build the OpenAPI request body schema for a webhook plugin route."""

    payload_schema = plugin.openapi_payload_schema
    if payload_schema is None:
        return None

    schema = payload_schema.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    schema.pop("$defs", None)

    return {
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": schema,
                }
            },
        }
    }


def build_webhook_openapi_schema(app: FastAPI) -> dict[str, Any]:
    """Build the webhook application's OpenAPI schema with merged payload defs."""

    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    component_schemas: dict[str, Any] = schema.setdefault("components", {}).setdefault(
        "schemas", {}
    )
    for plugin in get_app_context().plugins.webhooks.values():
        payload_schema = plugin.openapi_payload_schema
        if payload_schema is None:
            continue
        full_schema = payload_schema.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        nested_definitions: dict[str, Any] = full_schema.pop("$defs", {})
        component_schemas.update(nested_definitions)
        component_schemas[payload_schema.__name__] = full_schema

    app.openapi_schema = schema
    return schema


def merge_mounted_webhook_openapi(
    parent_schema: dict[str, Any],
    webhook_app: FastAPI,
    *,
    mount_path: str = "/webhooks",
) -> dict[str, Any]:
    """Merge mounted webhook paths and schema components into a parent schema."""

    webhook_schema = webhook_app.openapi()
    parent_paths: dict[str, Any] = parent_schema.setdefault("paths", {})

    for path, path_item in webhook_schema.get("paths", {}).items():
        merged_path = _join_openapi_path(mount_path, path)
        parent_paths[merged_path] = path_item

    parent_components: dict[str, Any] = parent_schema.setdefault(
        "components", {}
    ).setdefault("schemas", {})
    parent_components.update(webhook_schema.get("components", {}).get("schemas", {}))
    return parent_schema


def _join_openapi_path(prefix: str, path: str) -> str:
    """Join an OpenAPI mount prefix and path without duplicating slashes."""

    normalized_prefix = prefix.rstrip("/") or "/"
    normalized_path = path if path.startswith("/") else f"/{path}"
    if normalized_prefix == "/":
        return normalized_path
    return f"{normalized_prefix}{normalized_path}"
