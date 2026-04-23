"""Mountable FastAPI application for WayGate webhooks."""

from fastapi import FastAPI

from .handlers import create_webhook_router
from .openapi import build_webhook_openapi_schema


def create_webhook_app() -> FastAPI:
    """Create the standalone webhook ingress FastAPI sub-application."""

    app = FastAPI(
        title="WayGate Webhooks",
        description="Mountable webhook ingress for WayGate plugin endpoints.",
        version="0.1.0",
    )
    app.include_router(create_webhook_router())
    app.openapi = lambda: build_webhook_openapi_schema(app)
    return app
