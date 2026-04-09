# Graph Overlay Plan

This document is the design anchor for Epic `#8` issue `#41`: prototype a lineage-backed knowledge graph overlay.

## Purpose

WayGate already stores enough provenance to support a graph-oriented view of the live corpus, but it does not yet implement transitive traversal or graph-backed retrieval. This plan defines a prototype direction that builds directly on current metadata instead of introducing a parallel graph data model.

## Current Metadata Substrate

The current repository already persists the fields needed for a first graph overlay:

- `doc_id`: stable document node identifier.
- `lineage`: explicit ancestry references promoted into live frontmatter.
- `sources`: normalized source URIs promoted during publish.
- `source_hash`: content hash of the ingested raw source.
- `tags`: thematic grouping hints.
- `document_type`, `status`, and `visibility`: retrieval and lifecycle constraints.

These fields already live in markdown frontmatter and remain the only durable source for a future graph projection.

## Non-Negotiable Constraints

1. Live markdown plus frontmatter remains the source of truth.
2. Any graph representation is reconstructable from the live corpus.
3. Graph traversal must preserve the current visibility boundary.
4. The graph overlay must extend retrieval; it must not replace the baseline lexical path.
5. The design must stay database-agnostic at this stage.

## Recommended Representation

The recommended prototype direction is a derived property graph built from live documents.

### Node types

- `DocumentNode`: one node per live document, keyed by `doc_id`.
- `SourceNode`: optional normalized source node keyed by canonical source URI.
- `TopicNode`: optional derived node keyed by stable tag or thematic cluster identity.

The first prototype can stop at document nodes plus derived edges if that keeps the model simpler.

### Edge types

- `DERIVED_FROM`: document -> lineage target document when `lineage` references another `doc_id`.
- `BACKLINK`: inverse view of `DERIVED_FROM`, materialized or derived at query time.
- `SAME_SOURCE`: document <-> document when normalized `sources` overlap.
- `SIMILAR_TOPIC`: optional future edge when tags or retrieval similarity indicate a meaningful neighborhood.

Only `DERIVED_FROM` is core to the first prototype. The rest are optional derived overlays.

## Why A Derived Graph Instead Of A Parallel Metadata Model

The current metadata vocabulary already carries provenance and relationship hints. Adding a second authoritative graph schema would create avoidable drift between markdown frontmatter and the traversal layer. The graph overlay should therefore be treated like a search index: disposable, rebuildable, and subordinate to the live corpus.

## Suggested Architectural Boundary

Graph traversal should live in a separate adapter layer, not as an unconditional responsibility inside `LiveDocumentRepository`.

Recommended split:

- `LiveDocumentRepository`: remains the canonical loader, filter, and briefing assembler.
- `GraphOverlayBuilder`: derives nodes and edges from loaded live documents.
- `GraphTraversalAdapter`: expands candidate sets from lineage and backlink relationships.
- `RetrievalExpansionPolicy`: decides when graph expansion is allowed and how deep it may traverse.

These are design roles, not current code.

## Retrieval Augmentation Model

The recommended retrieval flow is:

1. Load and filter the live markdown corpus using the existing retrieval scope and metadata rules.
2. Run the baseline lexical or hybrid candidate selection.
3. Optionally expand the top candidate set through graph traversal.
4. Re-rank the expanded set with the existing scorer or a future fused scorer.
5. Assemble the briefing using the existing token-budgeted path.

This keeps graph traversal as an augmentation step instead of letting it bypass the current retrieval contract.

## Traversal Semantics

Recommended first traversal behaviors:

- One-hop lineage expansion from a selected document to its direct ancestors.
- One-hop backlink expansion from a selected document to direct descendants.
- Configurable depth limits, defaulting to one hop.
- Deterministic de-duplication by `doc_id`.

Deferred for later work:

- unrestricted recursive walks
- weighted graph centrality models
- graph-database-specific query languages
- cross-tenant or cross-visibility graph expansion

## Visibility And Safety Rules

- Visibility filtering remains mandatory before expanded candidates are returned.
- Graph edges must not reveal hidden documents indirectly through counts or labels.
- Traversal must operate on the effective retrieval scope, including MCP server-side scope clamping.
- Documents outside the allowed scope are treated as nonexistent for traversal.

## Backlink Strategy

Backlinks should be derived, not authored by hand.

- If document `B` lists document `A` in `lineage`, then `A` has a derived backlink to `B`.
- The backlink set should be rebuildable from the corpus without mutating stored frontmatter.
- This preserves a single write path during publish and avoids dual-write consistency problems.

## Relationship To Hybrid Retrieval

The graph overlay depends on the hybrid-search boundary from issue `#44`, but it does not require BM25 or vector infrastructure to exist first.

- The no-index lexical baseline can still feed graph expansion.
- Future BM25 or vector candidates can feed the same traversal adapter.
- Graph traversal should remain orthogonal to future semantic search adapters.

## Operational Model

The graph projection should behave like other secondary indexes.

- It can be built in memory for small corpora.
- It can later be persisted to a reconstructable local store if startup cost becomes too high.
- It may be rebuilt during maintenance or on demand.
- Failure to build the graph should degrade to normal retrieval rather than breaking briefing generation.

## Prototype Recommendation

For the first implementation-oriented prototype after this planning slice:

1. Add an in-memory graph overlay derived from `load_live_documents()`.
2. Support only document nodes and `DERIVED_FROM` plus derived backlinks.
3. Keep traversal depth at one hop.
4. Expose the result only behind an optional retrieval-expansion flag.

This is enough to validate the retrieval and provenance model without committing to a graph database.

## Acceptance Mapping For Issue #41

- Documented prototype direction: this document defines the graph model and traversal boundary.
- Grounded in repository metadata: the proposal uses `doc_id`, `lineage`, `sources`, `source_hash`, and current retrieval scope semantics.
- Future work can build from this: the builder, traversal, and expansion roles are explicit.

## Explicitly Deferred

- Production graph database rollout.
- Full graph-powered retrieval implementation.
- Automatic missing-context research dispatch.
- Human-facing lineage visualization.
