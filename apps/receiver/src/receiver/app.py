import asyncio
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI

from receiver.api import webhooks
from receiver.core.registry import IngestionPlugin, registry
from receiver.core.scheduler import setup_scheduler, scheduler
from receiver.services.trigger import save_and_trigger_langgraph_async

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.discover_and_register()

    setup_scheduler()
    scheduler.start()

    background_tasks = []
    for plugin in registry.get_all().values():
        if type(plugin).listen != IngestionPlugin.listen:
            task = asyncio.create_task(
                plugin.listen(on_data_callback=save_and_trigger_langgraph_async)
            )
            background_tasks.append(task)

    yield

    scheduler.shutdown()
    for task in background_tasks:
        task.cancel()


app = FastAPI(title="WayGate Receiver Ingestion API", lifespan=lifespan)

app.include_router(webhooks.router)
