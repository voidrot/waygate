# Setup & Running Locally

Minimal steps to get the project running for development:

1. Create and activate a Python venv, then install `uv`/workspace tools as needed.

2. Use `mise` helpers if available in this workspace. See `mise.toml` for configured tools.

3. Start required local services in `compose.yml` (e.g., `valkey`/Redis-like service):

```bash
docker compose -f compose.yml up -d
```

4. Run the receiver app for local testing (tools and commands depend on the member package layout). See each app's README for run instructions.
