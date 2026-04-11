import json
from waygate_core.plugin import WebhookVerificationError
from waygate_api.config import webhook_registry
from fastapi import APIRouter, Request, HTTPException

webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@webhook_router.post("/{plugin_name}")
async def handle_webhook(plugin_name: str, request: Request):
    """
    Handle an incoming webhook for a specific plugin.

    Args:
        plugin_name (str): The name of the plugin to route the webhook to.
        payload (dict): The JSON payload of the webhook.
    Returns:
        dict: A response indicating success or failure.
    """
    plugin = webhook_registry.get(plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")

    raw_body = await request.body()
    headers = dict(request.headers)

    try:
        await plugin.verify_webhook_request(headers, raw_body)
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        payload = await plugin.enrich_webhook_payload(payload, headers)
        raw_documents = await plugin.handle_webhook(payload)

        if raw_documents:
            # In a real implementation, you would likely want to do something with the raw documents,
            # such as saving them to a database or passing them to another part of your system.
            print(
                f"Plugin '{plugin_name}' produced {len(raw_documents)} raw documents."
            )

        return {
            "status": "success",
            "processed": len(raw_documents),
            "message": f"Webhook handled by plugin '{plugin_name}'",
        }

    except WebhookVerificationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc.msg}")
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail=f"Plugin '{plugin_name}' does not implement webhook handling",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
