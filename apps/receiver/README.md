# Receiver

The Receiver package accepts ingestion inputs (HTTP webhooks, scheduled polls,
or long-running listeners) and dispatches discovered documents into storage
and downstream processing.

Key files and locations:

- [app.py](apps/receiver/src/receiver/app.py) — application entry and bootstrap.
- [api/webhooks.py](apps/receiver/src/receiver/api/webhooks.py) — webhook HTTP endpoints.
- [api/health.py](apps/receiver/src/receiver/api/health.py) — basic health check endpoint.
- [core/scheduler.py](apps/receiver/src/receiver/core/scheduler.py) — scheduled polling integration.
- [core/registry.py](apps/receiver/src/receiver/core/registry.py) — plugin/service discovery.
- [services/trigger.py](apps/receiver/src/receiver/services/trigger.py) — orchestration for incoming events.

Testing

See the workspace `tests.rest` file for example webhook payloads that can be
posted to the receiver during local development.
