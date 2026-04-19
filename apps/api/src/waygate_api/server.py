from waygate_api.routes.webhooks.router import webhook_router
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from contextlib import asynccontextmanager
from typing import Any
from waygate_core import bootstrap_app, get_app_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_app()

    yield


app = FastAPI(
    title="WayGate API",
    description="API for WayGate",
    version="0.1.0",
    lifespan=lifespan,
)


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Merge each plugin's payload-schema definitions into components/schemas so
    # that $ref values like "#/components/schemas/Foo" (produced by router.py
    # via ref_template) resolve correctly in Swagger UI / ReDoc.
    component_schemas: dict = schema.setdefault("components", {}).setdefault(
        "schemas", {}
    )
    for plugin in get_app_context().plugins.webhooks.values():
        payload_schema = plugin.openapi_payload_schema
        if payload_schema is None:
            continue
        full = payload_schema.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        # $defs holds the nested-model definitions; hoist them to the top level.
        defs: dict = full.pop("$defs", {})
        component_schemas.update(defs)
        component_schemas[payload_schema.__name__] = full

    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi  # type: ignore[method-assign]  # ty:ignore[invalid-assignment]


FastAPIInstrumentor().instrument_app(app)

app.include_router(webhook_router)
