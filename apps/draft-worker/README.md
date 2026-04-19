# waygate-draft-worker

RQ worker process for WayGate draft workflow triggers.

## Running

```bash
uv run waygate-draft-worker
```

The worker bootstraps the WayGate app context, reads the configured
`communication-rq` settings, connects to Redis, and listens on the draft queue.

## Configuration

The worker consumes these environment-backed settings at runtime:

| Variable | Default | Description |
| --- | --- | --- |
| `WAYGATE_COMMUNICATION_RQ__REDIS_URL` | unset | Preferred Redis URL for the worker connection |
| `WAYGATE_COMMUNICATION_RQ__DRAFT_QUEUE_NAME` | `draft` | Queue name the worker listens on |
| `WAYGATE_CORE__REDIS_DSN` | `redis://localhost:6379/0` | Redis fallback when plugin `REDIS_URL` is not set |
| `WAYGATE_CORE__REDIS_URL` | unset | Legacy alias accepted by core as a Redis fallback |

The `communication-rq` plugin must be installed so `communication_rq` settings
are present in the merged WayGate config.
