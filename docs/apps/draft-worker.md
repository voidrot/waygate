# WayGate Draft Worker

The draft worker app is the RQ execution boundary for queued WayGate draft workflow triggers.

It consumes jobs from Redis, resolves the configured communication-rq settings, and executes the workflow entry point from `waygate-workflows`.

## What It Does

- Boots the shared WayGate app context.
- Resolves the worker Redis connection and queue name from `communication-rq` settings.
- Creates an RQ queue and worker for the draft workflow queue.
- Runs queued workflow triggers with scheduler integration disabled.

## Runtime Flow

1. `waygate_draft_worker.main()` bootstraps the shared runtime.
2. `_resolve_runtime()` validates that `communication-rq` configuration exists.
3. The worker connection is resolved from the plugin Redis URL or the core fallback Redis DSN.
4. The configured draft queue is bound to an RQ worker.
5. The worker starts processing jobs until it is stopped.

## Configuration

| Variable                                     | Default                    | Description                                                   |
| -------------------------------------------- | -------------------------- | ------------------------------------------------------------- |
| `WAYGATE_COMMUNICATION_RQ__REDIS_URL`        | unset                      | Preferred Redis URL for the worker.                           |
| `WAYGATE_COMMUNICATION_RQ__DRAFT_QUEUE_NAME` | `draft`                    | Queue name consumed by the worker.                            |
| `WAYGATE_CORE__REDIS_DSN`                    | `redis://localhost:6379/0` | Core Redis fallback when the plugin does not set a Redis URL. |
| `WAYGATE_CORE__REDIS_URL`                    | unset                      | Legacy alias accepted by the core config model.               |

## Entry Point

- `waygate_draft_worker:main` starts the worker process.

## Notes

- The worker fails fast if the `communication-rq` plugin is not installed or configured.
- The worker always uses the configured queue name and does not infer it from the job payload.
