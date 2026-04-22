# WayGate NATS Worker

The NATS worker app is the JetStream execution boundary for durable WayGate
workflow triggers.

## What It Does

- boots the shared WayGate app context
- validates the active compile LLM configuration before pulling work
- ensures the configured JetStream stream and consumers exist
- pulls `draft.ready` and `cron.tick` messages from JetStream
- runs the shared workflow router and settles each message with `ack`, `nak`, or `term`

## Configuration

| Variable                                        | Default                  | Description                                          |
| ----------------------------------------------- | ------------------------ | ---------------------------------------------------- |
| `WAYGATE_WORKER__SERVERS`                       | `nats://localhost:4222`  | NATS servers as JSON array or comma-delimited string |
| `WAYGATE_WORKER__STREAM_NAME`                   | `WAYGATE_WORKFLOW`       | JetStream stream used by the worker                  |
| `WAYGATE_WORKER__DRAFT_SUBJECT`                 | `waygate.workflow.draft` | Subject consumed for `draft.ready`                   |
| `WAYGATE_WORKER__CRON_SUBJECT`                  | `waygate.workflow.cron`  | Subject consumed for `cron.tick`                     |
| `WAYGATE_WORKER__DRAFT_CONSUMER_NAME`           | `waygate-draft`          | Durable consumer name for draft workflow messages    |
| `WAYGATE_WORKER__CRON_CONSUMER_NAME`            | `waygate-cron`           | Durable consumer name for cron workflow messages     |
| `WAYGATE_WORKER__ACK_WAIT_SECONDS`              | `30.0`                   | Lease window before JetStream redelivery             |
| `WAYGATE_WORKER__IN_PROGRESS_HEARTBEAT_SECONDS` | `15.0`                   | Lease renewal interval for active workflow jobs      |
| `WAYGATE_WORKER__MAX_DELIVER`                   | `3`                      | Maximum JetStream delivery attempts                  |
| `WAYGATE_WORKER__BACKOFF_SECONDS`               | `[10, 30, 60]`           | Redelivery backoff sequence for retryable failures   |

## Entry Point

- `waygate_nats_worker:main` starts the worker process.
