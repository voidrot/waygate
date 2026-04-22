"""Dynamic FastAPI webhook route registration."""

from collections.abc import Callable
import json

from fastapi import APIRouter, HTTPException, Request

from waygate_core import get_app_context
from waygate_core.files import compute_content_hash, render_raw_document
from waygate_core.logging import get_logger
from waygate_core.plugin import WebhookPlugin, WebhookVerificationError
from waygate_core.plugin.storage import StorageNamespace

from .dispatch import send_workflow_message
from .errors import map_dispatch_failure_to_http
from .openapi import build_webhook_openapi_extra

logger = get_logger()


def create_webhook_router(*, prefix: str = "") -> APIRouter:
    """Create a router with one POST route per discovered webhook plugin."""

    router = APIRouter(prefix=prefix, tags=["webhooks"])
    app_context = get_app_context()

    for plugin in app_context.plugins.webhooks.values():
        router.add_api_route(
            f"/{plugin.name}",
            _make_handler(plugin),
            methods=["POST"],
            summary=plugin.openapi_summary,
            description=plugin.description,
            openapi_extra=build_webhook_openapi_extra(plugin),
        )

    return router


def _make_handler(plugin: WebhookPlugin) -> Callable:
    """Build a FastAPI route handler bound to a single webhook plugin."""

    async def handle_webhook(request: Request) -> dict[str, object]:
        raw_body = await request.body()
        headers = dict(request.headers)

        try:
            await plugin.verify_webhook_request(headers, raw_body)
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            payload = await plugin.enrich_webhook_payload(payload, headers)
            raw_documents = await plugin.handle_webhook(payload)

            if raw_documents:
                written_paths = []
                storage = _resolve_storage_plugin()

                logger.debug(
                    "Plugin '%s' produced %s raw documents.",
                    plugin.name,
                    len(raw_documents),
                )

                for raw_document in raw_documents:
                    content_hash = raw_document.content_hash or compute_content_hash(
                        raw_document.content
                    )
                    path = (
                        storage.build_namespaced_path(
                            StorageNamespace.Raw, content_hash
                        )
                        + ".txt"
                    )
                    written_paths.append(
                        storage.write_document(path, render_raw_document(raw_document))
                    )

                written_paths = list(dict.fromkeys(written_paths))
                workflow_message = plugin.build_workflow_trigger(payload, written_paths)
                if workflow_message is not None:
                    dispatch_result = await send_workflow_message(workflow_message)
                    if not dispatch_result.accepted:
                        status_code, detail = map_dispatch_failure_to_http(
                            dispatch_result
                        )
                        raise HTTPException(status_code=status_code, detail=detail)

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

    handle_webhook.__name__ = f"handle_webhook_{plugin.name.replace('-', '_')}"
    return handle_webhook


def _resolve_storage_plugin():
    """Resolve the configured storage plugin from the shared app context."""

    app_context = get_app_context()
    return app_context.plugins.storage[app_context.config.core.storage_plugin_name]
