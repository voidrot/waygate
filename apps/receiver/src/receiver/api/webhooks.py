import json

from receiver.core.registry import registry
from fastapi import APIRouter, HTTPException, Request

from receiver.core.scheduler import save_and_trigger_langgraph_async
from waygate_core.plugin_base import WebhookVerificationError

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/{plugin_name}")
async def handle_webhook(plugin_name: str, request: Request):
    plugin = registry.get(plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
    raw_body = await request.body()
    headers = dict(request.headers)

    try:
        plugin.verify_webhook_request(headers, raw_body)
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        payload = plugin.prepare_webhook_payload(payload, headers)
        raw_documents = plugin.handle_webhook(payload)

        if raw_documents:
            await save_and_trigger_langgraph_async(raw_documents)
        return {"status": "success", "processed": len(raw_documents)}
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
