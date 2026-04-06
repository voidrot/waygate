from receiver.core.registry import registry
from fastapi import APIRouter, HTTPException, Request

from receiver.core.scheduler import save_and_trigger_langgraph_async

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/{plugin_name}")
async def handle_webhook(plugin_name: str, request: Request):
    plugin = registry.get(plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
    payload = await request.json()

    try:
        raw_documents = plugin.handle_webhook(payload)

        if raw_documents:
            await save_and_trigger_langgraph_async(raw_documents)
        return {"status": "success", "processed": len(raw_documents)}
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail=f"Plugin '{plugin_name}' does not implement webhook handling",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
