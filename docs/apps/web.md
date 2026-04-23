# WayGate Web

The web app is the primary HTTP and operator surface for WayGate.

It serves the server-rendered UI, initializes AuthTuna, mounts the shared webhook ingress app, and publishes a single OpenAPI surface that includes the mounted webhook routes.

The current UI scope is intentionally small: an anonymous control-plane splash, an authenticated wiki landing page, stub document or job or review pages, and shared auth and webhook ingress surfaces. It is not yet a full document management or workflow operations UI.

## What It Does

- Boots the shared WayGate app context.
- Validates that the configured communication plugin exists before serving requests.
- Initializes AuthTuna for browser and API-oriented auth flows.
- Serves WayGate-owned replacements for the AuthTuna HTML auth, account, organization, team, and email templates.
- Includes the page routes that render the anonymous splash, authenticated wiki landing, stub operator pages, and admin-only runtime page.
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
- `apps/web` keeps AuthTuna's backend route surface but replaces the default upstream templates with WayGate-owned Jinja pages and self-contained HTML email templates. Those templates are grouped by purpose under `waygate_web/templates/authtuna/auth`, `waygate_web/templates/authtuna/user`, and `waygate_web/templates/authtuna/email`, and the package-relative defaults are normalized to filesystem paths during startup.
- The current server-rendered pages are an infrastructure MVP for the web surface. The wiki, documents, jobs, and review pages now exist as route and template stubs, while broader operator workflows and live data wiring are still future work.
