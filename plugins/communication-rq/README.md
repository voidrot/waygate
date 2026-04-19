# waygate-plugin-communication-rq

Communication client plugin that enqueues `WorkflowTriggerMessage` payloads into
RQ queues backed by Redis.

## Behavior

- `draft.ready` messages go to the configured draft queue.
- `cron.tick` messages go to the configured cron queue.
- The plugin returns the RQ job ID in `WorkflowDispatchResult`.

## Configuration

Environment variables use the `WAYGATE_COMMUNICATION_RQ__*` namespace.

| Variable                                     | Default                                                 | Description                                    |
| -------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------- |
| `WAYGATE_COMMUNICATION_RQ__REDIS_URL`        | unset                                                   | Explicit Redis URL for enqueue operations      |
| `WAYGATE_COMMUNICATION_RQ__DRAFT_QUEUE_NAME` | `draft`                                                 | Queue name used for `draft.ready`              |
| `WAYGATE_COMMUNICATION_RQ__CRON_QUEUE_NAME`  | `cron`                                                  | Queue name used for `cron.tick`                |
| `WAYGATE_COMMUNICATION_RQ__JOB_FUNCTION`     | `waygate_workflows.draft.jobs.process_workflow_trigger` | Import path for worker job function            |
| `WAYGATE_COMMUNICATION_RQ__JOB_TIMEOUT`      | `5m`                                                    | RQ job timeout                                 |
| `WAYGATE_COMMUNICATION_RQ__RESULT_TTL`       | `500`                                                   | Seconds to retain successful job results       |
| `WAYGATE_COMMUNICATION_RQ__FAILURE_TTL`      | `31536000`                                              | Seconds to retain failed job results           |
| `WAYGATE_COMMUNICATION_RQ__RETRY_MAX`        | `3`                                                     | Maximum retry attempts                         |
| `WAYGATE_COMMUNICATION_RQ__RETRY_INTERVALS`  | `10,30,60`                                              | Retry intervals in seconds                     |
| `WAYGATE_COMMUNICATION_RQ__UNIQUE_JOBS`      | `true`                                                  | Enable RQ unique jobs when `job_id` is present |

Redis URL fallback order when `WAYGATE_COMMUNICATION_RQ__REDIS_URL` is not set:

1. `WAYGATE_CORE__REDIS_DSN`
2. `WAYGATE_CORE__REDIS_URL`
3. `redis://localhost:6379/0`
