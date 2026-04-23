"""FastAPI application assembly for the unified WayGate web app."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from waygate_core import get_app_context
from waygate_webhooks import create_webhook_app, merge_mounted_webhook_openapi

from .auth import configure_auth, initialize_auth_database
from .routes import page_router
from .settings import WaygateWebRuntimeSettings

web_settings = WaygateWebRuntimeSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bootstrap shared runtime state before the app starts serving requests."""

    await initialize_auth_database()
    get_app_context()
    yield


app = FastAPI(
    title=web_settings.title,
    description=web_settings.description,
    version=web_settings.version,
    lifespan=lifespan,
)

configure_auth(app)

webhook_app = create_webhook_app()
app.mount("/webhooks", webhook_app)
app.include_router(page_router)


def custom_openapi() -> dict[str, Any]:
    """Build the parent schema and merge in mounted webhook endpoints."""

    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    merge_mounted_webhook_openapi(schema, webhook_app, mount_path="/webhooks")
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

FastAPIInstrumentor().instrument_app(app)
