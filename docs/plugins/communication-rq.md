# Communication RQ Plugin

The communication RQ plugin is the Redis/RQ transport adapter for WayGate workflow triggers.

It enqueues serialized `WorkflowTriggerMessage` payloads into named RQ queues and returns RQ job identifiers in the dispatch result.

## What It Does

- Reads its own plugin config from `WAYGATE_COMMUNICATION_RQ__*` variables.
- Resolves the active Redis URL from plugin config or core fallbacks.
- Chooses a draft or cron queue based on the trigger event type.
- Builds stable job ids from the event type and idempotency key when available.
- Treats duplicate jobs as accepted so idempotent producers stay stable.

## Behavior

- `draft.ready` uses the draft queue.
- `cron.tick` uses the cron queue.
- Unsupported event types are rejected before enqueue.
- Redis connection errors are reported as transient failures.

## Configuration

| Variable                                     | Default                                                 | Description                                   |
| -------------------------------------------- | ------------------------------------------------------- | --------------------------------------------- |
| `WAYGATE_COMMUNICATION_RQ__REDIS_URL`        | unset                                                   | Preferred Redis URL for enqueue operations.   |
| `WAYGATE_COMMUNICATION_RQ__DRAFT_QUEUE_NAME` | `draft`                                                 | Queue used for `draft.ready` triggers.        |
| `WAYGATE_COMMUNICATION_RQ__CRON_QUEUE_NAME`  | `cron`                                                  | Queue used for `cron.tick` triggers.          |
| `WAYGATE_COMMUNICATION_RQ__JOB_FUNCTION`     | `waygate_workflows.draft.jobs.process_workflow_trigger` | Import path for the worker job function.      |
| `WAYGATE_COMMUNICATION_RQ__JOB_TIMEOUT`      | `5m`                                                    | RQ job timeout.                               |
| `WAYGATE_COMMUNICATION_RQ__RESULT_TTL`       | `500`                                                   | Result retention window in seconds.           |
| `WAYGATE_COMMUNICATION_RQ__FAILURE_TTL`      | `31536000`                                              | Failure retention window in seconds.          |
| `WAYGATE_COMMUNICATION_RQ__RETRY_MAX`        | `3`                                                     | Maximum retry attempts.                       |
| `WAYGATE_COMMUNICATION_RQ__RETRY_INTERVALS`  | `10,30,60`                                              | Retry delay sequence in seconds.              |
| `WAYGATE_COMMUNICATION_RQ__UNIQUE_JOBS`      | `true`                                                  | Enables unique jobs when a job id is present. |

## Entry Point

- `waygate.plugins.communication`

## Notes

- Redis URL fallback order is plugin config, then core Redis DSN, then the legacy core Redis URL alias, then localhost.
- The plugin is designed to work with the worker router provided by `waygate-workflows`.
# Communication RQ Plugin

The communication RQ plugin is the Redis/RQ transport adapter for WayGate workflow triggers.

It enqueues serialized `WorkflowTriggerMessage` payloads into named RQ queues and returns RQ job identifiers in the dispatch result.

## What It Does

- Reads its own plugin config from `WAYGATE_COMMUNICATION_RQ__*` variables.
- Resolves the active Redis URL from plugin config or core fallbacks.
- Chooses a draft or cron queue based on the trigger event type.
- Builds stable job ids from the event type and idempotency key when available.
- Treats duplicate jobs as accepted so idempotent producers stay stable.

## Behavior

- `draft.ready` uses the draft queue.
- `cron.tick` uses the cron queue.
- Unsupported event types are rejected before enqueue.
- Redis connection errors are reported as transient failures.

## Configuration

| Variable                                     | Default                                                 | Description                                   |
| -------------------------------------------- | ------------------------------------------------------- | --------------------------------------------- |
| `WAYGATE_COMMUNICATION_RQ__REDIS_URL`        | unset                                                   | Preferred Redis URL for enqueue operations.   |
| `WAYGATE_COMMUNICATION_RQ__DRAFT_QUEUE_NAME` | `draft`                                                 | Queue used for `draft.ready` triggers.        |
| `WAYGATE_COMMUNICATION_RQ__CRON_QUEUE_NAME`  | `cron`                                                  | Queue used for `cron.tick` triggers.          |
| `WAYGATE_COMMUNICATION_RQ__JOB_FUNCTION`     | `waygate_workflows.draft.jobs.process_workflow_trigger` | Import path for the worker job function.      |
| `WAYGATE_COMMUNICATION_RQ__JOB_TIMEOUT`      | `5m`                                                    | RQ job timeout.                               |
| `WAYGATE_COMMUNICATION_RQ__RESULT_TTL`       | `500`                                                   | Result retention window in seconds.           |
| `WAYGATE_COMMUNICATION_RQ__FAILURE_TTL`      | `31536000`                                              | Failure retention window in seconds.          |
| `WAYGATE_COMMUNICATION_RQ__RETRY_MAX`        | `3`                                                     | Maximum retry attempts.                       |
| `WAYGATE_COMMUNICATION_RQ__RETRY_INTERVALS`  | `10,30,60`                                              | Retry delay sequence in seconds.              |
| `WAYGATE_COMMUNICATION_RQ__UNIQUE_JOBS`      | `true`                                                  | Enables unique jobs when a job id is present. |

## Entry Point

- `waygate.plugins.communication`

## Notes

- Redis URL fallback order is plugin config, then core Redis DSN, then the legacy core Redis URL alias, then localhost.
- The plugin is designed to work with the worker router provided by `waygate-workflows`.
