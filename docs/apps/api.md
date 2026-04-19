# WayGate API

The API app is the HTTP ingress boundary for WayGate.

It uses FastAPI to expose one webhook route per discovered webhook plugin, writes produced raw documents to storage, and submits `draft.ready` trigger messages through the configured communication client.

## What It Does

- Boots the shared WayGate app context at startup.
- Validates that the configured communication plugin exists before serving requests.
- Mounts webhook routes dynamically from installed webhook plugins.
- Persists raw documents through the configured storage plugin.
- Dispatches workflow trigger messages after webhook processing succeeds.
- Merges per-plugin OpenAPI payload schemas into the application schema.

## Runtime Flow

1. `waygate_api.main()` bootstraps the shared core runtime.
2. The configured communication plugin is resolved eagerly so startup fails fast when misconfigured.
3. `waygate_api.server` constructs the FastAPI app and instruments it with OpenTelemetry.
4. Webhook plugins are discovered and registered under `/webhooks/<plugin-name>`.
5. Requests are verified, enriched, converted into raw documents, and stored.
6. Draft-ready trigger messages are submitted through the selected communication plugin.

## Configuration

| Variable | Default   | Description                          |
| -------- | --------- | ------------------------------------ |
| `HOST`   | `0.0.0.0` | Bind address for the Uvicorn server. |
| `PORT`   | `8080`    | Bind port for the Uvicorn server.    |

The API also reads all `WAYGATE_*` settings from `waygate-core`.

## Entry Points

- `waygate_api:main` starts the server process.
- `waygate_api.server:app` exposes the FastAPI application object.

## Notes

- OpenAPI payload schemas are merged at startup so plugin-specific request bodies resolve correctly in Swagger UI and ReDoc.
- Webhook handling is intentionally plugin-driven; adding a plugin adds a route.
