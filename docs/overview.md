# WayGate — Project Overview

WayGate is a modular knowledge ingestion and processing platform oriented around LLM-driven workflows. The project contains:

- `apps/compiler`: a workflow compiler/executor that builds and runs content transformation graphs.
- `apps/receiver`: HTTP/webhook receiver and scheduler for ingestion plugins.
- `libs/core`: shared core utilities, LLM provider abstractions, schemas, and plugin base classes.
- `libs/storage`: pluggable storage provider interfaces and registry.
- `plugins/*`: provider and storage plugin implementations (examples: Ollama LLM provider, local storage, generic webhook receiver plugin).

Current implementation focus (April 2026):

- Canonical metadata contract implemented from ingestion through publish.
- Local storage preserves and can query raw document metadata by `doc_id`.
- Compiler promotion includes provenance lineage/source propagation into live frontmatter.
- GitHub and Slack receiver plugins currently parse webhook payloads to canonical documents.

Explicitly out of scope for this milestone:

- Retrieval-filtering/RBAC enforcement engine across query transports.
- Broader cryptographic provenance systems beyond current hash + lineage fields.

Entry points and configuration

- `compose.yml`: simple compose file used for local services. See [compose.yml](compose.yml).
- `pyproject.toml`: workspace definition and member packages. See [pyproject.toml](pyproject.toml).

Testing

See `tests.rest` for example HTTP requests used to exercise the receiver and plugin interfaces.
