# Hybrid Retrieval Plan

This document is the design anchor for Epic `#8` issue `#44`: plan hybrid retrieval over markdown with BM25 and vector search.

## Purpose

WayGate already ships a deterministic lexical retrieval SDK over live markdown documents. This plan defines how future hybrid retrieval can extend that baseline without replacing markdown and frontmatter as the source of truth.

## Current Baseline

Implemented today:

- Live documents are enumerated from storage and parsed from markdown plus canonical YAML frontmatter.
- Visibility filtering runs before ranking.
- Metadata filtering runs before ranking.
- Ranking is deterministic and lexical through the `DocumentScorer` seam.
- Briefing assembly is token-budgeted and deterministic.
- Lineage is a direct filter and scoring boost, not a recursive graph traversal.

Not implemented today:

- BM25 indexing.
- Vector embeddings or semantic retrieval.
- LLM re-ranking.
- Recursive lineage expansion.
- External search infrastructure.

## Non-Negotiable Constraints

1. Live markdown and frontmatter remain the durable source of truth.
2. Any lexical, vector, or graph index is reconstructable from live markdown.
3. Visibility policy is enforced before results leave the retrieval boundary.
4. Hybrid retrieval must preserve the current retrieval request and briefing result contracts where practical.
5. Future search layers are adapters around the SDK, not a rewrite of the source-of-truth model.

## Planned Architecture

The target architecture is a staged retrieval pipeline with optional secondary indexes.

1. Source enumeration and metadata loading still begin from storage-backed live markdown.
2. A lexical adapter can provide BM25 or improved keyword retrieval over reconstructed document text.
3. A semantic adapter can provide vector similarity over reconstructed embeddings.
4. A fusion layer combines lexical and semantic candidate sets into one ranked pool.
5. An optional re-ranking stage can refine only the fused top-k results.
6. Existing briefing assembly produces the final token-budgeted output.

## Retrieval Layers

### Primary data layer

- `list_live_documents()` and `read_live_document()` remain authoritative.
- `FrontMatterDocument` remains the canonical metadata contract.
- Storage plugins are not required to become search engines.

### Secondary lexical layer

- BM25 or equivalent keyword retrieval is an optional adapter.
- The lexical index is derived from document title, tags, body, lineage, and selected frontmatter fields.
- Rebuilds can be full or incremental, but the index must be disposable and reproducible.

### Secondary semantic layer

- Vector search is an optional adapter fed by embeddings derived from live markdown.
- Embedding storage may be local, file-backed, or external later, but the embedding corpus must remain reproducible from live markdown.
- Semantic retrieval never becomes the only retrieval path.

### Fusion layer

- Hybrid retrieval combines lexical and semantic candidates into a common result set.
- Initial design should prefer simple fusion, such as weighted reciprocal rank fusion, over opaque heuristics.
- The fusion stage must preserve deterministic behavior for equal inputs and equal index state.

### Re-ranking layer

- Re-ranking is optional and top-k bounded.
- It may use a stronger lexical model, a cross-encoder, or an LLM later.
- Re-ranking must not bypass visibility or metadata filtering.

## Suggested SDK Evolution

The current `LiveDocumentRepository` and `DocumentScorer` seams are enough for a first hybrid design. The recommended evolution is:

1. Keep `RetrievalQuery`, `RetrievalScope`, `RetrievedLiveDocument`, and `BriefingResult` stable.
2. Introduce optional candidate-provider adapters rather than baking BM25 or vector concerns directly into storage.
3. Keep `DocumentScorer` as the ranking seam for the no-index baseline and for fallback operation.
4. Add a future fused-candidate path in `LiveDocumentRepository` rather than replacing the current deterministic path.

## Candidate Provider Model

Recommended future adapter roles:

- `MarkdownCorpusLoader`: loads canonical live documents from storage.
- `LexicalCandidateProvider`: returns lexical candidates and lexical scores.
- `SemanticCandidateProvider`: returns semantic candidates and semantic similarity scores.
- `CandidateFusionStrategy`: merges candidate sets into one normalized ranking input.
- `ResultReranker`: optional final refinement over bounded top-k results.

These are design roles, not current code.

## Lineage and Graph Relationship

Hybrid retrieval should stay separate from future graph traversal.

- BM25 and vector search operate over the current live corpus.
- Graph traversal remains a separate future concern under issue `#41`.
- Lineage can continue to act as a filter and boost in hybrid retrieval before transitive graph expansion is designed.

The graph-overlay direction for that later phase is documented in
`docs/graph_overlay_plan.md`.

## Operational Model

Indexes should behave like caches.

- They may be rebuilt from markdown at startup, on demand, or through a maintenance task.
- They must tolerate deletion and full rebuild.
- Maintenance findings and audit artifacts remain outside the search index itself.
- Search infrastructure failures should degrade to deterministic lexical retrieval, not break the SDK contract entirely.

## Security Model

- Visibility filtering remains mandatory before ranking output leaves the repository boundary.
- MCP server-side scope clamping continues to define the effective caller scope before retrieval.
- Hybrid search adapters must operate only on documents already allowed for the effective scope, or must filter before results are returned.

## Sequencing

Recommended follow-on order after this plan:

1. Prototype the graph-overlay direction in issue `#41`.
2. Design the missing-context research loop in issue `#42`.
3. Prototype structured-consensus compilation in issue `#40`.
4. Evaluate cryptographic provenance in issue `#43`.

## Acceptance Mapping For Issue #44

- Concrete hybrid-retrieval plan: this document defines the architecture, constraints, and sequencing.
- Markdown remains source of truth: the primary data and reconstructable-index rules are explicit.
- Later issues can use this as a design anchor: the adapter roles and sequencing are named directly.

## Explicitly Deferred

- Shipping a production BM25 engine.
- Shipping a production vector database.
- Implementing graph traversal in this issue.
- Adding LLM re-ranking in this issue.
- Replacing the existing deterministic retrieval path.
