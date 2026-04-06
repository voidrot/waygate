# WayGate — Project Overview

WayGate is a modular knowledge ingestion and processing platform oriented around LLM-driven workflows. The project contains:

- `apps/compiler`: a workflow compiler/executor that builds and runs content transformation graphs.
- `apps/receiver`: HTTP/webhook receiver and scheduler for ingestion plugins.
- `libs/core`: shared core utilities, LLM provider abstractions, schemas, and plugin base classes.
- `libs/storage`: pluggable storage provider interfaces and registry.
- `plugins/*`: provider and storage plugin implementations (examples: Ollama LLM provider, local storage, generic webhook receiver plugin).

Entry points and configuration

- `compose.yml`: simple compose file used for local services. See [compose.yml](compose.yml).
- `pyproject.toml`: workspace definition and member packages. See [pyproject.toml](pyproject.toml).

Testing

See `tests.rest` for example HTTP requests used to exercise the receiver and plugin interfaces.
