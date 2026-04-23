# waygate-plugin-communication-nats

Communication client plugin that publishes `WorkflowTriggerMessage` payloads to
NATS JetStream subjects.

## Behavior

- `draft.ready` messages go to the configured draft subject.
- `cron.tick` messages go to the configured cron subject.
- The plugin publishes with `Nats-Msg-Id` when an idempotency key is present.
- JetStream publish acknowledgements are returned in `WorkflowDispatchResult`.

## Configuration

Environment variables use the `WAYGATE_COMMUNICATION_NATS__*` namespace.

| Variable                                              | Default                      | Description                                          |
| ----------------------------------------------------- | ---------------------------- | ---------------------------------------------------- |
| `WAYGATE_COMMUNICATION_NATS__SERVERS`                 | `nats://localhost:4222`      | NATS servers as JSON array or comma-delimited string |
| `WAYGATE_COMMUNICATION_NATS__STREAM_NAME`             | `WAYGATE_WORKFLOW`           | Expected JetStream stream name                       |
| `WAYGATE_COMMUNICATION_NATS__DRAFT_SUBJECT`           | `waygate.workflow.draft`     | Subject used for `draft.ready`                       |
| `WAYGATE_COMMUNICATION_NATS__CRON_SUBJECT`            | `waygate.workflow.cron`      | Subject used for `cron.tick`                         |
| `WAYGATE_COMMUNICATION_NATS__CLIENT_NAME`             | `waygate-communication-nats` | Connection label shown in NATS monitoring            |
| `WAYGATE_COMMUNICATION_NATS__CONNECT_TIMEOUT_SECONDS` | `2.0`                        | Connect timeout for producer calls                   |
| `WAYGATE_COMMUNICATION_NATS__PUBLISH_TIMEOUT_SECONDS` | `5.0`                        | JetStream publish timeout                            |

## Notes

- The plugin expects a JetStream stream to exist and treats missing stream
  configuration as a configuration error.
- The `waygate-worker-app` process can create the stream automatically during
  worker startup for local development and simple deployments.
