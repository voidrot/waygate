# Communication NATS Plugin

The communication NATS plugin is the JetStream transport adapter for WayGate
workflow triggers.

It publishes serialized `WorkflowTriggerMessage` payloads to JetStream subjects
and returns a publish acknowledgement identifier in the dispatch result.

## What It Does

- reads its own plugin config from `WAYGATE_COMMUNICATION_NATS__*` variables
- chooses a draft or cron subject based on the trigger event type
- publishes through JetStream rather than best-effort core NATS pub/sub
- sets `Nats-Msg-Id` when an idempotency key is present so duplicate submissions can be deduplicated by JetStream

## Behavior

- `draft.ready` uses the configured draft subject
- `cron.tick` uses the configured cron subject
- unsupported event types are rejected before publish
- missing stream or JetStream configuration errors are reported as config failures
- NATS connectivity and timeout failures are reported as transient failures

## Configuration

| Variable                                              | Default                      | Description                                          |
| ----------------------------------------------------- | ---------------------------- | ---------------------------------------------------- |
| `WAYGATE_COMMUNICATION_NATS__SERVERS`                 | `nats://localhost:4222`      | NATS servers as JSON array or comma-delimited string |
| `WAYGATE_COMMUNICATION_NATS__STREAM_NAME`             | `WAYGATE_WORKFLOW`           | JetStream stream expected by the producer            |
| `WAYGATE_COMMUNICATION_NATS__DRAFT_SUBJECT`           | `waygate.workflow.draft`     | Subject used for `draft.ready`                       |
| `WAYGATE_COMMUNICATION_NATS__CRON_SUBJECT`            | `waygate.workflow.cron`      | Subject used for `cron.tick`                         |
| `WAYGATE_COMMUNICATION_NATS__CLIENT_NAME`             | `waygate-communication-nats` | Connection name shown in NATS monitoring             |
| `WAYGATE_COMMUNICATION_NATS__CONNECT_TIMEOUT_SECONDS` | `2.0`                        | Connect timeout for producer calls                   |
| `WAYGATE_COMMUNICATION_NATS__PUBLISH_TIMEOUT_SECONDS` | `5.0`                        | JetStream publish timeout                            |

## Notes

- This transport is designed to be paired with `waygate-nats-worker`.
- The worker can create the JetStream stream for local development and simple deployments.
