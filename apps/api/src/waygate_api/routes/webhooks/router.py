from waygate_api.clients import send_draft_message
from waygate_core.files.template import render_raw_document
from waygate_core.plugin.storage_base import StorageNamespace
from waygate_api.config.storage_registry import storage
from waygate_core.logging import get_logger
import json
from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Request

from waygate_api.config import webhook_registry
from waygate_core.plugin import WebhookPlugin, WebhookVerificationError

webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])

logger = get_logger()


def _make_handler(plugin: WebhookPlugin) -> Callable:
    """Return a FastAPI route handler closure bound to *plugin*."""

    async def handle_webhook(request: Request):
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
                            StorageNamespace.Raw, f"{plugin.name}/{doc.doc_id}"
                        )
                        + ".md"
                    )
                    written_paths.append(
                        storage.write_document(path, render_raw_document(doc))
                    )

                    send_draft_message(written_paths)

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
    """Build the ``openapi_extra`` requestBody for a plugin.

    Pydantic's ``model_json_schema`` emits nested-model definitions in a
    top-level ``$defs`` block with refs like ``#/$defs/Foo``.  Those refs are
    not valid at the OpenAPI document level; the resolver expects them in
    ``#/components/schemas/``.  We therefore generate the schema with the
    correct ``ref_template`` so every ``$ref`` already points at
    ``components/schemas``, and strip the (now-redundant) ``$defs`` block.
    The custom ``openapi()`` hook in ``server.py`` is responsible for merging
    those definitions into ``components/schemas`` when the spec is assembled.
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
for _plugin in webhook_registry.get_all().values():
    _openapi_extra = _build_openapi_extra(_plugin)

    webhook_router.add_api_route(
        f"/{_plugin.name}",
        _make_handler(_plugin),
        methods=["POST"],
        summary=_plugin.openapi_summary,
        description=_plugin.description,
        openapi_extra=_openapi_extra,
    )
