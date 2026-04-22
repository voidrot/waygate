# waygate-api

FastAPI HTTP server for WayGate. Exposes webhook ingestion endpoints and serves the OpenAPI schema with per-plugin payload definitions merged in automatically.

## Responsibilities

- Receives inbound webhook requests and routes them to the registered `WebhookPlugin` for the matched route.
- Persists produced raw documents and submits the workflow trigger built by the matched webhook plugin through the configured communication client plugin.
- Merges each webhook plugin's payload schema into the OpenAPI spec at startup so that `$ref` definitions resolve correctly in Swagger UI and ReDoc.
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
