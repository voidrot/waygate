# WayGate Core Library

## Testing

Run the core package tests from the package directory:

```bash
uv run pytest
```

From the repository root, the equivalent command is:

```bash
mise run test:core
```

Run `mise run uv:sync` from the repository root before running package-local tests
so the workspace packages are installed in editable mode.
