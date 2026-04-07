# WayGate: Generation-Augmented Retrieval (GAR) System Architecture

## Current Implementation Boundary (April 2026)

This architecture document mixes implemented components and forward-looking design. The following reflects current repository behavior:

Implemented now:

- Receiver normalizes ingestion plugin output to canonical `RawDocument` records and enqueues compile jobs.
- Local storage persists raw and live markdown documents with canonical YAML frontmatter.
- Compiler graph runs Draft -> Review -> Publish and writes live articles under `wiki/live`.
- Publish promotes provenance fields from raw metadata into live frontmatter (`lineage`, `sources`, aggregated `tags`).
- First-party GitHub and Slack receiver plugins parse webhook payloads into canonical document records.
- `libs/agent_sdk` loads live markdown documents, applies retrieval-scope visibility filtering, performs deterministic lexical scoring, and assembles token-budgeted briefings.
- `apps/mcp_server` exposes the SDK through FastMCP with `generate_briefing` and `preview_retrieval`, a health endpoint, and optional static bearer auth.

Not implemented in this milestone (explicitly out of scope):

- External IAM, scoped tokens, and end-user RBAC for downstream query consumers.
- Full provenance engine beyond current source hash + lineage frontmatter fields.
- Static-site deployment surfaces and non-lexical search backends described as target architecture.

## Executive Summary

**WayGate** is a Generation-Augmented Retrieval (GAR) system designed to autonomously compile raw, multi-source data (GitHub, Slack, Web) into a highly structured, self-healing Markdown wiki.

Operating on an elastic, Python-centric monorepo managed by `uv`, the system features a decoupled ingestion receiver and a LangGraph-powered compilation worker. WayGate prioritizes extreme modularity: its execution graphs support pre/post middleware hooks, dynamic prompt injection, and highly observable traces. Its deployment footprint scales seamlessly from sequential local generation to massive, queue-driven batch processing.

Instead of relying on fragmented vector retrievals, downstream agents and human users interact with WayGate's structured knowledge base through an internal retrieval SDK and a FastMCP server, while preserving room for future static-site and hybrid-search layers.

---

## 1. System Design, Directory Schema, & Metadata

The system treats the filesystem itself as the primary database. The topology is strictly segmented to isolate immutable data from LLM-generated synthesis, while consolidating configuration and handling execution fallouts.

### The WayGate Directory Topology

- **`raw/` (Immutable Source):** Managed exclusively by ingestion plugins (Tri-Mode Receiver). Contains webhooks, Git diffs, and Slack thread JSONs. Read-only for the compiler.
- **`live/` (The Compiled Wiki):** Managed exclusively by the LangGraph compiler. Contains the synthesized Markdown files categorized into `concepts/`, `entities/`, and `thematic/`.
- **`staging/` (Dead-Letter Queue):** When the LangGraph Draft Node fails the "Hermes Quality Gate" three consecutive times, the draft is dropped here, and a slack alert is fired for manual human review.
- **`meta/` (Architect Tier):** Consolidates system configuration.
  - `templates/` holds the Markdown validation templates used by the Draft Node.
  - `agents/` holds role overlays and context-anchoring for downstream agent swarms.

### The Unified YAML Frontmatter

To ensure the system is both auditable and self-healing, every document in the `live/` directory is stamped with a rigorous metadata block upon compilation.

```yaml
doc_id: "01HGW2X..."
title: "GAR System Architecture"
source_type: "github"
source_url: "[https://github.com/org/repo/pull/123](https://github.com/org/repo/pull/123)"
source_hash: "a2b4c6..."
status: "active"
visibility: "internal"
tags: ["architecture", "langgraph", "fastmcp"]
last_compiled: "2026-04-06T12:00:00Z"
lineage: ["01HGW2Y...", "01HGW2Z..."]
```

Provenance Pipeline: source_type, source_url, source_hash, and tags are extracted or injected during the FastAPI Ingestion phase.

Execution Pipeline: status, last_compiled, and lineage are dynamically managed by the LangGraph Compiler worker during the synthesis loop.

Security Pipeline: visibility is currently enforced inside the retrieval SDK using a caller-supplied retrieval scope, while transport auth is limited to optional static bearer middleware on the MCP server.

---

## 2\. Technical Requirements & Extensibility

WayGate operates on a highly asynchronous, Python-centric stack.

- **Core Stack:** Python (`uv` workspaces), FastAPI (Receiver), LangGraph (Compiler Worker), Valkey/Redis (Task Queue), LangChain.
- **Observability:** OpenTelemetry (OTel) and LangSmith for state tracing *(See Section 11).*
- **Pluggable Middleware Architecture:** The LangGraph nodes (`draft`, `review`, `publish`) utilize a Hook/Middleware pattern for dependency injection, Pre-Hooks (chunking/PII scrubbing), and Post-Hooks (human-in-the-loop alerts).

---

## 3\. Foundational Plugin Base

- **Ingestion Plugins:** GitHub/Git (codebase context), Slack (communication consensus), Web Clipper.
- **Storage Plugins:** Local File System (Base) and AWS S3 (Enterprise).
- **LLM Providers:** Abstracted interfaces supporting local models and cloud APIs. *(Model swaps are guarded by Eval Pipelines \- See Section 13).*

---

## 4\. High-Level Workflows and Patterns

### Tri-Mode Ingestion Pipeline

The FastAPI receiver standardizes inputs via Pull (Batch polling), Push (Webhooks), and Stream (Websockets/Socket Mode).

### LangGraph Compilation Loop

1. **Draft Node:** Raw strings are injected via XML tags and matched with a `templates/` schema to synthesize a Markdown article.
2. **Hermes Quality Gate:** A rigorous QA agent evaluates the draft for factual grounding and metadata compliance.
3. **Cyclic Review:** If rejected, feedback loops back to the Draft Node. After 3 failures, it triggers a `human_review` state.

---

## 5\. Agent Integration & SDK

### The `waygate_agent_sdk`

The current retrieval boundary lives in `libs/agent_sdk`. It loads live markdown from storage, parses canonical frontmatter, applies visibility and metadata filters, ranks documents with a deterministic lexical scorer, and assembles token-limited briefings.

### Dual Consumption Model

1. **Standard MCP Access:** The internal `apps/mcp_server` utilizes the SDK to expose `generate_briefing` and `preview_retrieval` over FastMCP. The current transport supports optional static bearer auth, but not scoped IAM.
2. **Native Internal Consumers:** Other workspace apps can depend on `waygate_agent_sdk` directly when they need retrieval or briefing assembly without going through MCP.

---

## 6\. Enhancements & Roadmap

- **Missing Context Loop:** Downstream agents detect context gaps and dispatch a "Research Agent" to scrape the web, updating the `raw/` directory and triggering a compile.
- **Structured Consensus:** Passing raw data through multiple, distinct models that cross-critique each other to resolve hallucinations.
- **Cryptographic Receipt Binding:** Hashing synthesized facts to original `raw/` sources using Ed25519 signatures.

---

## 7\. Suggested Technologies (Secondary Indexes)

The Markdown filesystem is the immutable source of truth; secondary indexes are reconstructable:

- **Vector Database (Milvus / Qdrant):** For "Hybrid Search" (Vector Semantic \+ BM25).
- **Graph Database (Neo4j):** To actualize a "Knowledge Graph Overlay" mapped from the YAML `lineage` tags.
- **Temporal.io:** To provide highly durable execution for long-running batch ingestion, replacing Valkey/Redis.

---

## 8\. Current Issues & Identified Improvements

1. **Context Limit Vulnerability (Chunking):** Implement an immediate Pre-Hook middleware to chunk massive repositories prior to the Draft phase.
2. **Dead-End `human_review` State:** Implement a Post-Hook to trigger an external UI notification (e.g., Slack) to allow human developers to resolve execution deadlocks.
3. **Single-Point Synthesis Failure:** Transition the base node configuration to the "Structured Consensus" multi-model pattern.

---

## 9\. Continuous Maintenance & Lifecycle Management Workflow

To maintain continuous parity between the `raw/` data ingestion tier and the `live/` wiki:

1. **Hash-Mismatch Invalidation:** Background cron jobs compare new raw SHA-256 hashes against the dependent `live/` document `source_hash`. Mismatches trigger an automatic Recompile Task.
2. **Chrono-Decay Sweeps:** Documents exceeding a designated TTL (based on `last_compiled`) trigger a Verification Agent. Unverified documents are downgraded to `stale_warning`.
3. **Agentic Feedback Loop:** Agents encountering context errors issue a `report_context_error` command, flagging the document for immediate Recompile or Human Review.
4. **Orphan Detection:** The compiler prunes the `lineage` graph. Documents pointing to missing raw sources are marked `archived` with a deprecation warning prepended to the Markdown.

---

## 10\. Thematic Synthesis & Tag Aggregation Workflow

To prevent downstream agents from exhausting token limits reading granular micro-documents, a "Synthesis Worker" provides macro-level roll-ups.

- **Execution:** A LangGraph node scans the `live/` directory for specific `tags` or `lineage` clusters. It drafts a high-level architectural overview, flagging any detected contradictions among the granular docs.
- **Output:** The new document is classified as `document_type: thematic_overview`. The Briefing SDK preferentially serves this overview to agents querying broad topics.

---

## 11\. Telemetry, Observability, & Auditing

Asynchronous, multi-agent workflows are highly susceptible to silent failures. WayGate requires a robust observability layer to trace the lifecycle of a document from raw webhook to compiled wiki.

- **OpenTelemetry (OTel) Backbone:** The current implementation now exposes an optional OTel helper in `libs/core`. When `OTEL_ENABLED=true`, the receiver configures tracing at startup and emits spans around scheduled polling and queue enqueue, while the compiler emits spans around worker execution and node wrappers. The existing application-level `trace_id` remains the cross-process correlation field and is attached as a span attribute.
- **No-op by default:** Local development remains dependency-light in behavior even though the packages are present; if `OTEL_ENABLED` is unset or false, the tracing helper does not configure a provider and span calls are effectively no-op.
- **LangGraph Auditing (LangSmith / Langfuse):** Hosted LLM-observability vendors remain optional follow-on integrations. This first wave stops at the OTel seam plus durable audit artifacts rather than introducing a vendor lock-in path.

---

## 12\. Human-Centric Presentation Layer (Static Site)

While agents consume knowledge via the SDK, human stakeholders require a highly readable, navigable interface.

- **Static Site Generator (SSG):** The system integrates a build-step utilizing an SSG like MkDocs (Material Theme) or Docusaurus.
- **Automated CI/CD:** A background worker watches the `live/` directory. Upon a `publish` event from the LangGraph worker, the SSG rebuilds the static site and deploys it to a standard internal web server.
- **Metadata Rendering:** The SSG is configured to parse the YAML frontmatter and render it visually. `visibility` becomes a security badge, `status` becomes a color-coded banner, and `lineage` can be rendered as an interactive D3.js graph at the bottom of the page, allowing humans to visually explore the knowledge base.

---

## 13\. Automated Evaluation Framework (LLM Ops)

The internal "Hermes Quality Gate" (Section 4\) handles real-time draft reviews, but the system architecture itself requires evaluation to prevent regressions when modifying prompts or swapping underlying LLM providers (Section 3).

- **The Golden Dataset:** WayGate maintains a static repository of complex `raw/` inputs and their human-approved `live/` outputs.
- **Eval Pipeline (DeepEval / Ragas):** Before any code merged into the compiler (`prompts/`, `templates/`, or `llm_registry.py`) is deployed, it must pass an automated CI/CD evaluation pipeline.
- **Metrics:** The new configuration generates drafts against the Golden Dataset, and the Eval framework scores the output on Factual Consistency, Contextual Relevancy, and Markdown Formatting adherence. A score drop blocks the deployment.

---

## 14\. Access Control Boundary

Current behavior:

- **Retrieval-layer visibility enforcement:** The SDK accepts a caller-supplied `RetrievalScope` and removes documents whose `visibility` is not allowed before ranking or briefing assembly.
- **Optional transport auth:** The FastMCP service can require a static bearer token via `MCP_AUTH_ENABLED` and `MCP_AUTH_TOKEN`.
- **Hard block:** Documents outside the allowed visibility set never enter the ranked result set or final briefing payload.

Future work:

- Scoped JWT/API-key claims mapped into retrieval scopes.
- External IAM integration and end-user transport authorization.
