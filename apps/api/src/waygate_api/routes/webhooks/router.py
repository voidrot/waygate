"""Dynamic webhook routing for the WayGate API app."""

from uuid import uuid7
from waygate_core import get_app_context
from waygate_api.clients import send_draft_message
from waygate_api.routes.webhooks.errors import map_dispatch_failure_to_http
from waygate_core.files import render_raw_document
from waygate_core.plugin.storage import StorageNamespace
from waygate_core.logging import get_logger
import json
from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Request

from waygate_core.plugin import (
    WebhookPlugin,
    WebhookVerificationError,
)

webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])

logger = get_logger()
app_context = get_app_context()
storage = app_context.plugins.storage[app_context.config.core.storage_plugin_name]


def _make_handler(plugin: WebhookPlugin) -> Callable:
    """Build a FastAPI route handler for a webhook plugin.

    Args:
        plugin: The webhook plugin to bind to the route handler.

    Returns:
        An async FastAPI route handler closure.
    """

    async def handle_webhook(request: Request):
        """Handle a webhook request for the bound plugin.

        Args:
            request: The incoming FastAPI request.

        Returns:
            A JSON-compatible success payload.
        """

        raw_body = await request.body()
        headers = dict(request.headers)

        try:
            await plugin.verify_webhook_request(headers, raw_body)
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            payload = await plugin.enrich_webhook_payload(payload, headers)
            raw_documents = await plugin.handle_webhook(payload)

            if raw_documents:
                logger.debug(
                    f"Plugin '{plugin.name}' produced {len(raw_documents)} raw documents."
                )
                written_paths = []
                for doc in raw_documents:
                    path = (
                        storage.build_namespaced_path(
                            StorageNamespace.Raw, f"{uuid7()}"
                        )
                        + ".txt"
                    )
                    written_paths.append(
                        storage.write_document(path, render_raw_document(doc))
                    )

                dispatch_result = await send_draft_message(written_paths)
                if not dispatch_result.accepted:
                    status_code, detail = map_dispatch_failure_to_http(dispatch_result)
                    raise HTTPException(status_code=status_code, detail=detail)

                logger.debug(
                    f"Plugin '{plugin.name}' wrote {len(written_paths)} documents to storage: {written_paths}"
                )

            return {
                "status": "success",
                "processed": len(raw_documents),
                "message": f"Webhook handled by plugin '{plugin.name}'",
            }

        except WebhookVerificationError as exc:
            raise HTTPException(status_code=401, detail=str(exc))
        except HTTPException:
            raise
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid JSON payload: {exc.msg}"
            )
        except NotImplementedError:
            raise HTTPException(
                status_code=501,
                detail=f"Plugin '{plugin.name}' does not implement webhook handling",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    # Give the function a unique name so FastAPI uses distinct operation IDs per plugin.
    handle_webhook.__name__ = f"handle_webhook_{plugin.name.replace('-', '_')}"
    return handle_webhook


def _build_openapi_extra(plugin: WebhookPlugin) -> dict | None:
    """Build the OpenAPI request-body schema for a webhook plugin.

    Pydantic emits nested-model definitions in ``$defs`` by default. The API
    server later hoists those definitions into ``components/schemas`` so the
    generated OpenAPI document resolves correctly in Swagger UI and ReDoc.

    Args:
        plugin: The webhook plugin whose payload schema should be exported.

    Returns:
        The ``openapi_extra`` mapping for the plugin route, or ``None`` when the
        plugin does not declare a payload schema.
    """
    payload_schema = plugin.openapi_payload_schema
    if payload_schema is None:
        return None

    schema = payload_schema.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    # $defs are populated into components/schemas by the server-level openapi()
    # override; drop them here so they don't appear inside the requestBody.
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


# Dynamically register one route per discovered plugin so each endpoint has
# its own OpenAPI entry with a plugin-supplied schema and description.
for _plugin in app_context.plugins.webhooks.values():
    _openapi_extra = _build_openapi_extra(_plugin)

    webhook_router.add_api_route(
        f"/{_plugin.name}",
        _make_handler(_plugin),
        methods=["POST"],
        summary=_plugin.openapi_summary,
        description=_plugin.description,
        openapi_extra=_openapi_extra,
    )
