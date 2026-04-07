# **Architectural Standards for Markdown-Based Generation-Augmented Retrieval Systems**

## Implementation Status (WayGate, April 2026)

The sections below describe the broader GAR design space. This section records the currently implemented contract in this repository.

Implemented now:

- Canonical metadata fields on raw/live models: `doc_id`, `source_type`, `source_url`, `source_hash`, `status`, `visibility`, `tags`, `last_compiled`, `lineage`, `sources`, `source_metadata`.
- `SourceMetadataBase` requires `kind` and permits extra provider-specific keys for forward-compatible round-tripping.
- Local storage writes canonical raw frontmatter and supports metadata fetch by doc id via `get_raw_document_metadata`.
- Compiler publish promotes provenance from raw metadata into live frontmatter: lineage from raw `doc_id`, sources from raw `source_url` (with URI fallback), and aggregated tags.
- Receiver trigger now passes structured raw metadata into compiler graph state for draft/review/publish usage.
- The retrieval SDK now loads live markdown, applies caller-supplied visibility policy, performs deterministic lexical ranking, and assembles token-budgeted briefing payloads.
- The MCP app exposes that SDK through FastMCP with briefing and retrieval-preview tools.

Out of scope for this milestone:

- External IAM, scoped tokens, and end-user RBAC across query surfaces.
- Vector search backends, BM25 indexes, and LLM re-ranking beyond the current scorer seams.
- Advanced provenance engines (for example cryptographic receipt/signature chains); current provenance is frontmatter lineage plus `source_hash`.

The paradigm of artificial intelligence is currently undergoing a fundamental transition from stateless, ephemeral interaction models toward persistent, compounding knowledge architectures. Standard Retrieval-Augmented Generation (RAG) frameworks have historically treated data as a collection of fragmented vector chunks, a method that frequently leads to the degradation of hierarchical context and the erosion of semantic relationships between disparate pieces of information.1 In response to these limitations, the Generation-Augmented Retrieval (GAR) pattern has emerged as a superior alternative, drawing inspiration from structured knowledge bases and multi-agent swarm concepts.3 Within a GAR system, a large language model (LLM) acts not merely as a passive search engine but as an autonomous background worker that continuously ingests raw data and synthesizes it into a human-readable, machine-accessible "Live Wiki".2 By utilizing Markdown as the primary medium, these systems establish a transparent, auditable, and version-controlled environment that bridges the gap between human oversight and automated processing.5

## **The Convergence of Human Readability and Machine Accessibility**

The selection of Markdown as the foundational substrate for a GAR system is a strategic decision rooted in its unique positioning as a format that is both intuitive for human readers and structurally parseable for AI agents.6 Markdown provides a rich set of semantic signals through its syntax, where headings indicate thematic hierarchy, bold text signals priority, and fenced code blocks provide clear boundaries for technical data.8 This structural clarity is instrumental in reducing token consumption compared to heavier formats like PDF or HTML, which can be three to five times more resource-intensive due to unnecessary ornamentation and boilerplate.8 For an AI model, a well-formatted Markdown document is easier to segment and parse, facilitating higher accuracy in generated responses by allowing the model to distinguish between instructions, questions, and factual conclusions.8

The implementation of a GAR system necessitates a directory structure and metadata schema that can support the continuous evolution of a knowledge base while maintaining strict data lineage and provenance.4 The system architecture is typically organized into a monorepo, often managed through modern tooling like uv workspaces to handle decoupled services such as ingestion receivers, compilers, and Model Context Protocol (MCP) servers.3 This modular approach ensures that the knowledge base is not locked into a specific vendor and remains a durable asset that can be re-indexed or modified without loss of underlying truth.2

## **Core Directory Topology for Multi-Source Ingestion**

A robust directory structure for a GAR system must clearly delineate between raw, immutable source data and the synthesized, version-controlled knowledge artifacts.4 The following topology is designed to organize submissions by source type while facilitating a clear progression from ingestion to publication.18

The physical filesystem acts as the primary database, segmenting immutable source data from synthesized knowledge, system configuration, and dead-letter queues.

```text
wiki/
├── raw/                # Immutable source of truth (Ingestion tier)
│   ├── github/         # Raw markdown from repo diffs
│   ├── slack/          # Exported thread JSONs
│   └── web/            # Scraped HTML/Markdown
├── live/               # The "Compiled Wiki" (Markdown + YAML)
│   ├── concepts/       # Atomic technical ideas and definitions
│   ├── entities/       # Dossiers on people, teams, or organizations
│   └── thematic/       # Macro-level roll-ups from Synthesis Workers
├── staging/            # Dead-letter queue for drafts that failed Quality Assurance loops
├── meta/               # System configurations and context anchors (Architect tier)
│   ├── templates/      # Schema enforcement and generation templates
│   └── agents/         # Role overlays for downstream swarms
```

The raw/ directory serves as the sacred repository of original documents, including research papers, Slack threads, and GitHub repositories.4 It is critical that the LLM has read access but no write permissions to this directory, ensuring that every claim in the synthesized wiki can be traced back to its original source for human verification or correction.5 Subdirectories within raw/ should be categorized by source type to maintain the unique structure of each origin, such as chronological folders for Slack or branch-specific folders for GitHub.22

The live/ directory contains the "Compiled Wiki," which is the codebase of synthesized knowledge entirely owned and maintained by the LLM maintainer.4 This layer does not simply index files for later retrieval but integrates new information into existing articles, revising summaries and flagging contradictions as the knowledge base grows.1 Navigational files such as index.md provide a content-oriented catalog, while log.md maintains a chronological audit trail of ingests, queries, and maintenance lints.1

## **Global Metadata Schema and YAML Frontmatter Standards**

Metadata is the mechanism through which a GAR system transforms a passive collection of files into a queryable knowledge graph.25 To ensure that documents are both human-readable and machine-accessible, the system must utilize YAML frontmatter—a block of key-value content at the top of every Markdown file.6 The fundamental rule of GAR metadata is that the data and its descriptive metadata must reside in the same file, traveling together without the need for an external relational database.6

### **Required Global Metadata Fields**

A core set of metadata fields is required for all documents to ensure interoperability across the system and to provide agents with the context necessary for high-precision retrieval.27

- `doc_id` (`UUID/ULID`, ingestion/compiler): unique persistent identifier.
- `title` (`String`, both): human-readable title for UI and rendering.
- `source_type` (`Enum`, ingestion): categorizes origin (`github`, `slack`, `web`, `synthesis`).
- `source_url` (`URL`, ingestion): direct link to the raw data or API origin.
- `source_hash` (`SHA-256`, ingestion): cryptographic tie to `raw/`; triggers auto-recompile if changed.
- `status` (`Enum`, compiler): lifecycle execution state (`draft`, `active`, `stale_warning`, `archived`).
- `visibility` (`Enum`, both): retrieval-layer visibility filtering input.
- `tags` (`Array`, ingestion): supports aggregation and retrieval narrowing.
- `last_compiled` (`ISO 8601`, compiler): used by chrono-decay sweeps to flag stale documents.
- `lineage` (`Array`, compiler): recursive `doc_id` links for mapping document ancestry.

The visibility field is currently enforced inside the retrieval layer through a caller-supplied scope of allowed visibilities, preventing sensitive documents from entering the ranking or final briefing output. The source\_hash field ensures that the system is self-healing; when a query is performed, the system can compare the current raw file hash against the hash recorded at the time of synthesis to identify stale or invalid claims.1

## **Source-Specific Metadata Enrichment Strategies**

While a core schema provides global consistency, a GAR system must accommodate the unique characteristics of different data sources.24 This is achieved through "plugin-specific" metadata blocks that capture the technical and operational context of the origin.3

### **GitHub and Technical Repository Integration**

GitHub repositories provide dense, structured information that requires careful conversion to Markdown to maintain its semantic utility.23 When a repository is ingested, the system must capture not just the file contents but the state of the codebase, including branches, commits, and ownership.23

| Key          | Description                          | AI Contextual Benefit                                       |
| :----------- | :----------------------------------- | :---------------------------------------------------------- |
| repo\_name   | Full repository identifier.          | Distinguishes between internal and external code.           |
| branch       | The specific branch ingested.        | Prevents confusion between main and feature code.           |
| commit\_sha  | Unique commit identifier.            | Ensures technical documentation matches a specific build.   |
| owner        | The team or developer responsible.   | Directs the agent to the correct human for clarification.   |
| tech\_stack  | Detected languages/frameworks.       | Helps agents select the correct "skill" or reasoning style. |
| token\_count | Estimated token size of the article. | Assists in context window management and budgeting.         |

Advanced ingestion tools like codefetch and folder2md4llms allow for the creation of single-file "codebase context" documents, which are optimized for LLM consumption by ignoring lock files, binaries, and media.23 These tools can also generate an automated tree view of the repository, providing the model with a mental map of the project structure before it begins analyzing individual files.37

### **Slack and Conversational Intelligence**

The challenge of ingesting Slack messages lies in transforming conversational "noise" into structured, actionable knowledge.24 Slack data is typically multi-topic and chronological; therefore, a GAR system must employ LLM-driven segmentation to break messages into semantically meaningful units.24

| Key             | Description                               | Strategic Utility                                           |
| :-------------- | :---------------------------------------- | :---------------------------------------------------------- |
| channel\_id     | Unique ID of the channel.                 | Essential for query-time permission checks.                 |
| thread\_ts      | Parent message timestamp.                 | Groups related replies into a coherent context.             |
| participants    | List of contributors to the conversation. | Tracks individual expertise and decision-makers.            |
| semantic\_type  | (Decision, Risk, Update, Blocker).        | Allows agents to filter for "all risks" or "all decisions". |
| anchor\_id      | Linked entity (Jira ID, Sprint ID).       | Connects chats to structured product management data.       |
| reaction\_ratio | Ratio of positive to negative emojis.     | Provides implicit human feedback on response quality.       |

The synthesis of Slack data into a wiki often focuses on a Q\&A-centric structure, where the system extracts clear questions and comprehensive answers from messy threads.41 By labeling these segments with "anchors" to core entities—such as a specific product launch or a Jira epic—the system creates a dynamic memory layer that evolves alongside the team's communication.24

### **Website Bookmarks and Research Provenance**

Web-based content, ingested via tools like the Obsidian Web Clipper, requires robust metadata to ensure that images and diagrams are preserved and that external sources are properly attributed.1

| Key           | Description                         | Metadata Goal                                             |
| :------------ | :---------------------------------- | :-------------------------------------------------------- |
| author        | The creator of the web content.     | Establishes the credibility of the source material.       |
| clipped\_at   | Timestamp of the web clip.          | Records when the information was deemed valid.            |
| domain        | The top-level domain of the source. | Enables filtering by trusted academic or technical sites. |
| local\_assets | Path to downloaded images.          | Permits multi-modal LLMs to "see" charts and diagrams.    |
| keywords      | SEO meta-tags from the page.        | Facilitates keyword-based retrieval alongside semantic.   |

Provenance is further strengthened by cryptographically binding each synthesized fact to its source.1 This can be achieved through content hashing or even git-commit-per-fact signatures, ensuring that the knowledge base satisfies regulatory audits and remains resilient against hallucinations.1

## **The Monorepo Architecture and Ingestion Pipeline**

The technical implementation of a GAR system is best realized through a decoupled, multi-service architecture sharing common core libraries.3 This approach allows for the independent scaling of ingestion, compilation, and retrieval services while maintaining a unified schema across the entire lifecycle of a document.3

### **Tri-Mode Ingestion Receiver**

The ingestion service, typically a FastAPI-driven application, must support three distinct modes of operation to accommodate the variety of source types required for a comprehensive knowledge base.3 The "Pull" or "Batch" mode uses schedulers like APScheduler to poll APIs for full repository syncs or periodic Slack exports.3 The "Push" or "Event" mode utilizes webhooks to receive data from external tools like the Obsidian Web Clipper.3 Finally, the "Stream" or "Continuous" mode maintains persistent connections, such as Slack's Socket Mode, to capture real-time conversational updates.3

Regardless of the ingestion mode, the receiver's primary responsibility is to normalize all inputs into a standard RawDocument schema defined in the core library.3 This standardization ensures that downstream compiler agents do not need to understand the intricacies of each source API, allowing them to focus entirely on synthesis and structuring.3

### **The LangGraph Compiler and Hermes Quality Gate**

The conversion of raw documents into structured wiki pages is managed by an asynchronous worker daemon executing a deterministic state graph, often built with frameworks like LangGraph.3 The pipeline begins at the "Draft Node," where raw strings are injected into an LLM prompt—often using XML tags for better segmentation—to synthesize a comprehensive Markdown article.3

The "Hermes Quality Gate" acts as a critical checkpoint before any article is published.3 This QA agent strictly enforces formatting, tone, and factual grounding against the raw data, rejecting any draft that exhibits hallucinations or structural violations.3

![][image1]
In this model, ![][image2] represents the drafted article and ![][image3] represents the raw source. If the approval flag is set to zero, the qualitative feedback is fed back into the Draft Node for a revision cycle.3 Only articles that pass this rigorous review are wrapped in YAML frontmatter and saved to the live/ directory.3

## **Retrieval Engineering and the MCP Briefing Engine**

The primary access layers for human developers and downstream swarm agents are the internal retrieval SDK and the Model Context Protocol (MCP) server built on top of it. The MCP service exposes the "Live Wiki" through a small suite of tools without bypassing the SDK boundary.

### **The Briefing Generation Workflow**

Instead of providing an agent with raw search results, the briefing engine compiles a strict, token-limited contextual package from live markdown. The current implementation filters by visibility and metadata, scores with deterministic lexical signals plus lineage boosts, then applies recency-based tie-breaks before assembling the final briefing.

- Visibility filter: mandatory. Removes documents outside the caller's allowed visibility set.
- Metadata filters: mandatory. Applies `document_type`, `status`, `tags`, and `lineage_ids` narrowing.
- Lexical score: high importance. Weights title matches highest, then tag matches, then body matches.
- Lineage boost: medium importance. Adds deterministic relevance when requested lineage intersects.
- Recency tie-break: secondary. Uses `last_compiled`, then `last_updated` to order equal scores.

This briefing serves as the agent's memory for a specific turn, ensuring that the model has deep, accurate context before executing any tools or making decisions. The current implementation uses direct metadata and lineage matching rather than a recursive knowledge-graph traversal, but preserves extension points for richer search backends later.

### **Hybrid Search Strategies for Scalability**

While a purely content-oriented index works effectively at moderate scales, the current SDK is intentionally hybrid-search-ready rather than hybrid-search-complete. The first release keeps the filesystem as the source of truth and ships only the deterministic lexical path, while leaving room for richer secondary indexes later.

1. **Current path:** Deterministic lexical scoring over live markdown plus recency tie-breaks.
2. **Planned path:** Optional BM25 or vector indexes as reconstructable secondary layers.
3. **Planned path:** Optional re-ranking adapters without changing the SDK request/response contract.

By maintaining the Markdown files as the "source of truth" on the local filesystem, the vector index becomes a secondary, reconstructable layer.17 If the index is deleted, it can be entirely rebuilt by re-embedding the structured Markdown files, ensuring that the knowledge base remains durable and future-proof.17

## **Autonomous Maintenance and Self-Healing Knowledge**

A central tenet of the GAR pattern is that the LLM is responsible for the "disciplined maintenance" of the wiki, a task that often involves periodic "linting" passes to ensure health and consistency.2 These health checks scan the knowledge base for several critical issues that could degrade the quality of the retrieved context.4

### **Linting for Contradictions and Staleness**

As new sources—such as updated Slack threads or new GitHub commits—are ingested, they may contradict existing articles in the wiki.1 The linting pass identifies these discrepancies, noting where new data challenges the evolving synthesis and flagging those articles for human or autonomous review.1 Similarly, the system identifies "stale claims" that have been superseded by more recent documentation.1

### **Identification of Knowledge Gaps**

A sophisticated GAR system is capable of detecting when its current knowledge is insufficient to answer a specific query.3 During a briefing generation, if the engine identifies a "context gap," it can asynchronously dispatch a Research Agent to find the missing data in the raw/ sources or perform a web search.3 This researcher then updates the wiki and returns the new information to the main agent loop, creating a self-expanding intelligence layer.3

## **Governance, Security, and Consensus**

The transition of a knowledge base from a human-managed repository to an AI-maintained asset introduces new requirements for governance and security.14 This is addressed through a combination of structured consensus, cryptographic provenance, and role-based access control (RBAC).1

### **Structured Consensus Models**

Instead of relying on a single model to write a summary or synthesis, a GAR system can implement structured consensus.1 This involves running a raw document through multiple independent models, which then cross-critique each other's outputs.1 The final synthesized article explicitly marks where the models agreed, where they diverged, and where they remained uncertain.1 This structural consensus provides a higher degree of confidence than a traditional "editorial" synthesis, which may inherit the biases or hallucinations of a single model.1

### **Cryptographic Receipt Binding**

To satisfy the requirements of high-stakes environments—such as financial institutions or healthcare—each knowledge artifact should record its derivation history.1 Every compiled wiki page includes a source provenance block in its metadata, recording the URIs of the original sources, their SHA-256 hashes, and the timestamps of ingestion.1 In advanced implementations, this can be extended to Ed25519 signatures, creating a cryptographic trail for every fact stored in the system.1

## **Conclusion: The Maturity of Personal and Enterprise Intelligence**

The directory structure and metadata schema for a Markdown-based GAR system represent the technical realization of Karpathy's "Wiki pattern" for autonomous knowledge work.3 By shifting the burden of "bookkeeping"—updating cross-references, maintaining summaries, and tracking provenance—from humans to machines, GAR systems allow human experts to focus on sourcing, exploration, and asking the right questions.1 The resulting knowledge asset is not a static repository but a living, compounding artifact that grows more valuable with every ingestion and every query.1

As these systems evolve, the integration of Knowledge Graph overlays and autonomous research agents will further bridge the gap between unstructured communication and actionable insight.3 The result is a single "pane of glass" through which a developer or an agent can navigate the totality of an organization's intelligence with the precision and context of a long-tenured expert.21 This architecture ensures that knowledge is no longer a collection of "black box" vectors but a transparent, self-healing foundation for the future of agentic intelligence.
