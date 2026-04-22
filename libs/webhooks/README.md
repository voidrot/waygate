# waygate-webhooks

Reusable FastAPI webhook ingress for WayGate.

## Responsibilities

- Builds one webhook endpoint per discovered `WebhookPlugin`
- Verifies signatures, enriches payloads, writes raw documents, and dispatches workflow triggers
- Exposes a mountable FastAPI sub-application for `/webhooks`
- Owns webhook-specific OpenAPI request-body and schema merge helpers

## Usage

```python
from fastapi import FastAPI

from waygate_webhooks import create_webhook_app, merge_mounted_webhook_openapi

app = FastAPI()
webhook_app = create_webhook_app()
app.mount("/webhooks", webhook_app)
```
