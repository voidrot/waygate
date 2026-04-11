# WayGate API Server

## Testing

Run the API tests from the package directory:

```bash
uv run pytest
```

From the repository root, the equivalent command is:

```bash
mise run test:api
```

Run `mise run uv:sync` from the repository root before running package-local tests
so the workspace packages are installed in editable mode.
