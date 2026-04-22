"""FastAPI application assembly for the legacy WayGate API app."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from waygate_core import get_app_context
from waygate_webhooks.handlers import create_webhook_router
from waygate_webhooks.openapi import build_webhook_openapi_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bootstrap shared runtime state before the app starts serving requests."""

    get_app_context()

    yield


app = FastAPI(
    title="WayGate API",
    description="Legacy WayGate webhook ingress service.",
    version="0.1.0",
    lifespan=lifespan,
)


def custom_openapi() -> dict[str, object]:
    """Build the OpenAPI schema for the legacy API webhook surface."""

    return build_webhook_openapi_schema(app)


app.openapi = custom_openapi  # type: ignore[method-assign]  # ty:ignore[invalid-assignment]


FastAPIInstrumentor().instrument_app(app)

app.include_router(create_webhook_router(prefix="/webhooks"))
