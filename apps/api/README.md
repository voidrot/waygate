# waygate-api

Legacy FastAPI webhook ingress for WayGate. This package is retained during the migration to `apps/web`, but it now delegates webhook route registration and OpenAPI schema helpers to `waygate-webhooks`.

## Responsibilities

- Receives inbound webhook requests and routes them to the registered `WebhookPlugin` for the matched route.
- Persists produced raw documents and submits the workflow trigger built by the matched webhook plugin through the configured communication client plugin.
- Reuses the shared webhook OpenAPI merge helpers from `waygate-webhooks` so the legacy ingress surface stays aligned with the new unified web app.
- Bootstraps the WayGate application context (config + plugins) on startup via `waygate-core`.
- Instruments the application with OpenTelemetry via `opentelemetry-instrumentation-fastapi`.

The default webhook behavior still emits `draft.ready`, but dedicated plugins can attach metadata, stable idempotency keys, or suppress dispatch when they need a different ingress shape.

## Running

```bash
uv run waygate-api
```

| Variable | Default   | Description  |
| -------- | --------- | ------------ |
| `HOST`   | `0.0.0.0` | Bind address |
| `PORT`   | `8080`    | Bind port    |

All `WAYGATE_*` environment variables are also read — see [`waygate-core`](../../libs/core/) for the full reference.

## OpenAPI

The schema is available at `/openapi.json`. Interactive docs are at `/docs` (Swagger UI) and `/redoc`.

The long-term operator surface is `apps/web`, but `apps/api` remains available as a migration-era ingress-only app.
