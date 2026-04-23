# WayGate Apps

This section documents the runtime apps in the WayGate monorepo.

## Apps

- [Web](web.md): Unified FastAPI host for the minimal server-rendered control plane, auth flows, and mounted webhook ingress.
- [Worker App](worker-app.md): Primary transport-agnostic worker app that resolves its listener from the configured communication plugin.
- [Scheduler](scheduler.md): APScheduler-based cron runner that dispatches recurring workflow triggers.

## Common Runtime Model

All runtime apps bootstrap the shared `waygate-core` runtime.

That means they all rely on the same merged `WaygateRootSettings` object, the same plugin discovery mechanism, and the same process-wide app context memoization.

Each app then layers a different responsibility on top of that shared core:

- the web app turns inbound HTTP requests into raw documents and plugin-built workflow triggers
- the worker app resolves the configured worker-side transport companion and runs the shared workflow handoff
- the scheduler emits cron-trigger messages for installed cron plugins

## Related References

- [libs/core](../../libs/core/)
- [docs/design/architecture.md](../design/architecture.md)
- [docs/design/runtime-and-plugins.md](../design/runtime-and-plugins.md)
- [docs/design/ingestion-and-workflows.md](../design/ingestion-and-workflows.md)
