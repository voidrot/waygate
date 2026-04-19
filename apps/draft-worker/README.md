# waygate-draft-worker

RQ worker process for WayGate draft workflow triggers.

## Running

```bash
uv run waygate-draft-worker
```

The worker bootstraps the WayGate app context, reads the configured
`communication-rq` settings, connects to Redis, and listens on the draft queue.
