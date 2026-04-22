# waygate-web

Unified FastAPI application for WayGate.

## Responsibilities

- Hosts the server-rendered operator UI with Jinja templates, HTMX fragments, and daisyUI styling
- Initializes AuthTuna for browser and API-oriented auth flows
- Mounts the reusable `waygate-webhooks` ingress sub-application at `/webhooks`
- Merges webhook OpenAPI endpoints into the parent app's docs so the unified app remains the primary surface

## Running

```bash
uv run waygate-web
```

## Auth Defaults

The app seeds local-development AuthTuna settings when auth environment variables are absent. These defaults are intended only for local development and should be overridden in deployed environments.
