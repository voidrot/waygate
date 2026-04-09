# WayGate — Project Overview

WayGate is a modular knowledge ingestion and processing platform oriented around LLM-driven workflows. The project contains:

- `apps/compiler`: a workflow compiler/executor that builds and runs content transformation graphs.
- `apps/receiver`: HTTP/webhook receiver and scheduler for ingestion plugins.
- `apps/mcp_server`: FastMCP-backed briefing service exposing the retrieval boundary over HTTP.
- `libs/core`: shared core utilities, LLM provider abstractions, schemas, and plugin base classes.
- `libs/agent_sdk`: internal retrieval and briefing SDK for live markdown documents.
- `libs/storage`: pluggable storage provider interfaces and registry.
- `plugins/*`: provider and storage plugin implementations (examples: Ollama LLM provider, local storage, generic webhook receiver plugin).

Current implementation focus (April 2026):

- Canonical metadata contract implemented from ingestion through publish.
- Local storage preserves and can query raw document metadata by `doc_id`.
- Compiler promotion includes provenance lineage/source propagation into live frontmatter.
- GitHub and Slack receiver plugins currently parse webhook payloads to canonical documents.
- Retrieval now loads compiled live markdown through an internal SDK with deterministic filtering, lexical scoring, lineage narrowing, and token-budgeted briefing assembly.
- The MCP server exposes the retrieval SDK through FastMCP with a health endpoint and optional static bearer auth controlled by environment variables.

Explicitly out of scope for this milestone:

- External IAM, scoped tokens, and end-user RBAC across retrieval transports.
- Non-lexical search backends such as vector indexes or LLM re-ranking adapters.
- Broader cryptographic provenance systems beyond current hash + lineage fields.

Roadmap anchors:

- Future hybrid retrieval planning is captured in `docs/hybrid_retrieval_plan.md`.
- Future graph-overlay planning is captured in `docs/graph_overlay_plan.md`.
- Future missing-context loop planning is captured in `docs/missing_context_loop_plan.md`.
- Future structured-consensus planning is captured in `docs/structured_consensus_plan.md`.
- Future cryptographic provenance evaluation is captured in `docs/cryptographic_provenance_plan.md`.
- Future thematic synthesis planning is captured in `docs/thematic_synthesis_plan.md`.
- Future static-site publishing planning is captured in `docs/static_site_publishing_plan.md`.
- Future operator-facing metadata view planning is captured in `docs/operator_metadata_view_plan.md`.

Entry points and configuration

- `compose.yml`: simple compose file used for local services. See [compose.yml](compose.yml).
- `pyproject.toml`: workspace definition and member packages. See [pyproject.toml](pyproject.toml).

Testing

See `tests.rest` for example HTTP requests used to exercise the receiver and plugin interfaces.
