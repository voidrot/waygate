# Communication HTTP Plugin

The communication HTTP plugin is the HTTP transport adapter for WayGate workflow triggers.

It sends `WorkflowTriggerMessage` payloads to a worker endpoint and translates HTTP failures into structured `WorkflowDispatchResult` values.

## What It Does

- Reads its own plugin config from `WAYGATE_COMMUNICATION_HTTP__*` variables.
- Posts trigger messages as JSON to the configured worker endpoint.
- Retries transient failures with exponential backoff.
- Maps request validation and transport failures into explicit dispatch error kinds.

## Behavior

- `draft.ready` requires at least one document path.
- The response body is used only for a JSON `message_id` field.
- 5xx responses and selected retryable HTTP statuses are treated as transient.
- Empty endpoints are treated as configuration errors.

## Configuration

| Variable                                            | Default                                   | Description                                         |
| --------------------------------------------------- | ----------------------------------------- | --------------------------------------------------- |
| `WAYGATE_COMMUNICATION_HTTP__ENDPOINT`              | `http://localhost:8090/workflows/trigger` | Worker endpoint receiving workflow trigger JSON.    |
| `WAYGATE_COMMUNICATION_HTTP__TIMEOUT_SECONDS`       | `5`                                       | Request timeout in seconds.                         |
| `WAYGATE_COMMUNICATION_HTTP__MAX_RETRIES`           | `2`                                       | Number of retry attempts after the initial request. |
| `WAYGATE_COMMUNICATION_HTTP__RETRY_BACKOFF_SECONDS` | `0.25`                                    | Base delay for exponential backoff.                 |
| `WAYGATE_COMMUNICATION_HTTP__AUTH_TOKEN`            | unset                                     | Optional auth token header value.                   |
| `WAYGATE_COMMUNICATION_HTTP__AUTH_HEADER`           | `Authorization`                           | Header name used when an auth token is configured.  |

## Entry Point

- `waygate.plugins.communication`

## Notes

- This plugin is transport-only; it does not execute workflows itself.
- It is suitable when an HTTP worker service is available behind the configured endpoint.
