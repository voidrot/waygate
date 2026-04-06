# WayGate: Generation-Augmented Retrieval (GAR) System Architecture

## Executive Summary

**WayGate** is a Generation-Augmented Retrieval (GAR) system designed to autonomously compile raw, multi-source data (GitHub, Slack, Web) into a highly structured, self-healing Markdown wiki.

Operating on an elastic, Python-centric monorepo managed by `uv`, the system features a decoupled ingestion receiver and a LangGraph-powered compilation worker. WayGate prioritizes extreme modularity: its execution graphs support pre/post middleware hooks, dynamic prompt injection, and highly observable traces. Its deployment footprint scales seamlessly from sequential local generation to massive, queue-driven batch processing.

Instead of relying on fragmented vector retrievals, downstream agents and human users interact with WayGate's structured knowledge base through securely scoped consumption layers, including a publishable Python SDK, a FastMCP server, and an auto-generated static frontend.

---

## 1. System Design, Directory Schema, & Metadata

The system treats the filesystem itself as the primary database. The topology is strictly segmented to isolate immutable data from LLM-generated synthesis, while consolidating configuration and handling execution fallouts.

### The WayGate Directory Topology

* **`raw/` (Immutable Source):** Managed exclusively by ingestion plugins (Tri-Mode Receiver). Contains webhooks, Git diffs, and Slack thread JSONs. Read-only for the compiler.
* **`live/` (The Compiled Wiki):** Managed exclusively by the LangGraph compiler. Contains the synthesized Markdown files categorized into `concepts/`, `entities/`, and `thematic/`.
* **`staging/` (Dead-Letter Queue):** When the LangGraph Draft Node fails the "Hermes Quality Gate" three consecutive times, the draft is dropped here, and a slack alert is fired for manual human review.
* **`meta/` (Architect Tier):** Consolidates system configuration.
  * `templates/` holds the Markdown validation templates used by the Draft Node.
  * `agents/` holds role overlays and context-anchoring for downstream agent swarms.

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

Security Pipeline: visibility is rigidly enforced at the transport layer by FastMCP (see Section 14) to prevent agents from accessing unauthorized data.

---

## 2\. Technical Requirements & Extensibility

WayGate operates on a highly asynchronous, Python-centric stack.

* **Core Stack:** Python (`uv` workspaces), FastAPI (Receiver), LangGraph (Compiler Worker), Valkey/Redis (Task Queue), LangChain.
* **Observability:** OpenTelemetry (OTel) and LangSmith for state tracing *(See Section 11).*
* **Pluggable Middleware Architecture:** The LangGraph nodes (`draft`, `review`, `publish`) utilize a Hook/Middleware pattern for dependency injection, Pre-Hooks (chunking/PII scrubbing), and Post-Hooks (human-in-the-loop alerts).

---

## 3\. Foundational Plugin Base

* **Ingestion Plugins:** GitHub/Git (codebase context), Slack (communication consensus), Web Clipper.
* **Storage Plugins:** Local File System (Base) and AWS S3 (Enterprise).
* **LLM Providers:** Abstracted interfaces supporting local models and cloud APIs. *(Model swaps are guarded by Eval Pipelines \- See Section 13).*

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

### The `waygate-agent-sdk`

All Briefing Engine logic—filtering the wiki via YAML `visibility` tags, traversing `lineage` graphs, and compiling token-limited contexts—is abstracted into `libs/waygate-agent-sdk`.

### Dual Consumption Model

1. **Standard MCP Access:** The internal `apps/mcp_server` utilizes the SDK to expose the `generate_briefing` tool to IDEs and generalized swarm agents. *(Secured via Scoped Tokens \- See Section 14).*
2. **Native Custom Agents:** Developers can `pip install waygate-agent-sdk` directly into proprietary codebases to dynamically manipulate the knowledge graph natively.

---

## 6\. Enhancements & Roadmap

* **Missing Context Loop:** Downstream agents detect context gaps and dispatch a "Research Agent" to scrape the web, updating the `raw/` directory and triggering a compile.
* **Structured Consensus:** Passing raw data through multiple, distinct models that cross-critique each other to resolve hallucinations.
* **Cryptographic Receipt Binding:** Hashing synthesized facts to original `raw/` sources using Ed25519 signatures.

---

## 7\. Suggested Technologies (Secondary Indexes)

The Markdown filesystem is the immutable source of truth; secondary indexes are reconstructable:

* **Vector Database (Milvus / Qdrant):** For "Hybrid Search" (Vector Semantic \+ BM25).
* **Graph Database (Neo4j):** To actualize a "Knowledge Graph Overlay" mapped from the YAML `lineage` tags.
* **Temporal.io:** To provide highly durable execution for long-running batch ingestion, replacing Valkey/Redis.

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

* **Execution:** A LangGraph node scans the `live/` directory for specific `tags` or `lineage` clusters. It drafts a high-level architectural overview, flagging any detected contradictions among the granular docs.
* **Output:** The new document is classified as `document_type: thematic_overview`. The Briefing SDK preferentially serves this overview to agents querying broad topics.

---

## 11\. Telemetry, Observability, & Auditing

Asynchronous, multi-agent workflows are highly susceptible to silent failures. WayGate requires a robust observability layer to trace the lifecycle of a document from raw webhook to compiled wiki.

* **OpenTelemetry (OTel) Backbone:** The system implements standard OTel tracing. A unique `trace_id` is generated at the FastAPI Receiver. This ID is passed through the Valkey/Redis queue payload and injected into the LangGraph worker state, creating a unified trace of the entire ingestion-to-publish lifecycle.
* **LangGraph Auditing (LangSmith / Langfuse):** The LangGraph compiler natively integrates with an LLM observability platform (like LangSmith or the open-source Langfuse). This provides granular UI dashboards to inspect exact prompt inputs, Hermes Review logic loops, token consumption, and generation latency per node.

---

## 12\. Human-Centric Presentation Layer (Static Site)

While agents consume knowledge via the SDK, human stakeholders require a highly readable, navigable interface.

* **Static Site Generator (SSG):** The system integrates a build-step utilizing an SSG like MkDocs (Material Theme) or Docusaurus.
* **Automated CI/CD:** A background worker watches the `live/` directory. Upon a `publish` event from the LangGraph worker, the SSG rebuilds the static site and deploys it to a standard internal web server.
* **Metadata Rendering:** The SSG is configured to parse the YAML frontmatter and render it visually. `visibility` becomes a security badge, `status` becomes a color-coded banner, and `lineage` can be rendered as an interactive D3.js graph at the bottom of the page, allowing humans to visually explore the knowledge base.

---

## 13\. Automated Evaluation Framework (LLM Ops)

The internal "Hermes Quality Gate" (Section 4\) handles real-time draft reviews, but the system architecture itself requires evaluation to prevent regressions when modifying prompts or swapping underlying LLM providers (Section 3).

* **The Golden Dataset:** WayGate maintains a static repository of complex `raw/` inputs and their human-approved `live/` outputs.
* **Eval Pipeline (DeepEval / Ragas):** Before any code merged into the compiler (`prompts/`, `templates/`, or `llm_registry.py`) is deployed, it must pass an automated CI/CD evaluation pipeline.
* **Metrics:** The new configuration generates drafts against the Golden Dataset, and the Eval framework scores the output on Factual Consistency, Contextual Relevancy, and Markdown Formatting adherence. A score drop blocks the deployment.

---

## 14\. Advanced Security & Access Control (IAM)

To prevent agents from hallucinating or exfiltrating sensitive organizational data, the `visibility` YAML tags (Section 1\) must be enforced at the transport layer.

* **Scoped API Tokens:** Downstream swarm agents cannot anonymously query the FastMCP Briefing Server. They must authenticate using scoped JWTs or API keys that define their authorized role (e.g., `role: infrastructure_agent`, `role: hr_assistant`).
* **Enforcement Engine:** When an agent issues a `generate_briefing` request, the FastMCP server intercepts the request. It cross-references the agent's token scope against the `visibility` tags of the retrieved documents.
* **Hard Block:** If an agent without `clearance: confidential` attempts to pull a document tagged `visibility: strictly_confidential`, the SDK strips that document from the context window entirely before returning the briefing payload.
