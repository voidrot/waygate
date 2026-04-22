# WayGate Apps

This section documents the runtime apps in the WayGate monorepo.

## Apps

- [API](api.md): FastAPI ingress service for webhook handling and trigger dispatch.
- [Draft Worker](draft-worker.md): RQ worker that consumes draft workflow triggers.
- [NATS Worker](nats-worker.md): JetStream worker that consumes durable workflow triggers.
- [Scheduler](scheduler.md): APScheduler-based cron runner that dispatches recurring workflow triggers.

## Common Runtime Model

All runtime apps bootstrap the shared `waygate-core` runtime.

That means they all rely on the same merged `WaygateRootSettings` object, the same plugin discovery mechanism, and the same process-wide app context memoization.

Each app then layers a different responsibility on top of that shared core:

- the API turns inbound HTTP requests into raw documents and plugin-built workflow triggers
- the draft worker executes queued workflow triggers from RQ
- the NATS worker executes durable workflow triggers from JetStream
- the scheduler emits cron-trigger messages for installed cron plugins

## Related References

- [libs/core](../../libs/core/)
- [docs/design/architecture.md](../design/architecture.md)
- [docs/design/runtime-and-plugins.md](../design/runtime-and-plugins.md)
- [docs/design/ingestion-and-workflows.md](../design/ingestion-and-workflows.md)
