# waygate-plugin-communication-rq

Communication client plugin that enqueues `WorkflowTriggerMessage` payloads into
RQ queues backed by Redis.

## Behavior

- `draft.ready` messages go to the configured draft queue.
- `cron.tick` messages go to the configured cron queue.
- The plugin returns the RQ job ID in `WorkflowDispatchResult`.

## Configuration

Environment variables use the `WAYGATE_COMMUNICATION_RQ__*` namespace.

- `REDIS_URL`
- `DRAFT_QUEUE_NAME`
- `CRON_QUEUE_NAME`
- `JOB_FUNCTION`
- `JOB_TIMEOUT`
- `RESULT_TTL`
- `FAILURE_TTL`
- `RETRY_MAX`
- `RETRY_INTERVALS`
- `UNIQUE_JOBS`
