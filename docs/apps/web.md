# WayGate Web

The web app is the primary HTTP and operator surface for WayGate.

It serves the server-rendered UI, initializes AuthTuna, mounts the shared webhook ingress app, and publishes a single OpenAPI surface that includes the mounted webhook routes.

The current UI scope is intentionally small: a minimal control-plane dashboard plus shared auth and webhook ingress surfaces. It is not yet a full document management or workflow operations UI.

## What It Does

- Boots the shared WayGate app context.
- Validates that the configured communication plugin exists before serving requests.
- Initializes AuthTuna for browser and API-oriented auth flows.
- Includes the page routes that render the minimal control-plane UI.
- Mounts the shared `waygate-webhooks` ingress app under `/webhooks`.
- Merges webhook payload schemas into the parent OpenAPI document.

## Runtime Flow

1. `waygate_web.main()` bootstraps the shared core runtime.
2. The configured communication plugin is resolved eagerly so startup fails fast when misconfigured.
3. `waygate_web.server` constructs the FastAPI app and instruments it with OpenTelemetry.
4. AuthTuna routes are initialized on the parent app.
5. The server-rendered page routes are included.
6. The shared webhook ingress app is mounted under `/webhooks`.
7. The parent app merges the mounted webhook OpenAPI schema into `/openapi.json`.

## Entry Points

- `waygate_web:main` starts the server process.
- `waygate_web.server:app` exposes the FastAPI application object.

## Notes

- Webhook handling is intentionally plugin-driven; adding a webhook plugin adds a route through `libs/webhooks` and makes it visible in the web app's OpenAPI output.
- Auth routes and webhook routes share the same parent FastAPI host, so the web app is the primary ingress surface for local development and deployment.
- The current server-rendered pages are an infrastructure MVP for the web surface; broader operator workflows are still future work.
