from waygate_api.routes.webhooks import webhook_router
from waygate_core.logging import configure_logging
from fastapi import FastAPI

configure_logging()

app = FastAPI(
    title="WayGate API",
    description="API for WayGate",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(webhook_router)
