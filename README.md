# WayGate

## Testing

Run the full test suite from the repository root:

```bash
mise run test
```

Run a single package suite from the repository root:

```bash
mise run test:core
mise run test:api
```

Run package-local tests from inside a package directory:

```bash
cd packages/core && uv run pytest
cd apps/api && uv run pytest
```

The repository uses a uv workspace with editable installs, so run `mise run uv:sync`
from the repository root before running tests from a package directory.
