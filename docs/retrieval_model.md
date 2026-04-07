# Retrieval Model

This document defines the first retrieval contract for WayGate's live markdown
documents and serves as the design anchor for Epic #6 issue #30.

## Scope

The first implementation targets filesystem-backed live markdown documents with
canonical YAML frontmatter. It does not require a vector database or external
IAM provider. Secondary indexes remain reconstructable and optional.

## Source of Truth

- Live documents are enumerated from storage via `list_live_documents()`.
- Document content is loaded via `read_live_document()`.
- Frontmatter is parsed into `FrontMatterDocument` and treated as the canonical
  retrieval metadata contract.
- Any future lexical or vector index is derived from live markdown and is not
  the source of truth.

## Retrieval Request Contract

The retrieval layer accepts a request with these inputs:

- `query`: free-text search string.
- `max_documents`: upper bound on returned ranked results.
- `token_budget`: maximum estimated token count for the final briefing output.
- `tags`: required tag filters.
- `document_types`: required `document_type` filters.
- `statuses`: allowed lifecycle statuses.
- `lineage_ids`: optional lineage anchors for narrowing the candidate set.

The caller also provides a retrieval scope containing the visibilities that are
allowed for that consumer.

## Pipeline Order

The retrieval pipeline runs in a strict order:

1. Enumerate live documents from storage.
2. Parse and normalize frontmatter metadata.
3. Apply visibility policy filtering.
4. Apply metadata filters for type, status, tags, and lineage.
5. Score remaining documents.
6. Sort by score, then by recency, then by stable title/URI tie-breakers.
7. Trim to `max_documents`.
8. Assemble briefing sections until the token budget is exhausted.

This ordering is intentional: unauthorized documents must never participate in
ranking, and token budgeting is the final assembly concern rather than a search
filter.

## Visibility Semantics

The first implementation performs visibility enforcement entirely inside the
retrieval layer. It accepts a caller-supplied scope with allowed visibilities
and excludes non-matching documents before ranking.

Current default behavior allows:

- `public`
- `internal`

while excluding `strictly_confidential` unless the caller explicitly expands its
allowed visibility set.

This is a retrieval-layer policy only. It does not yet implement external auth,
token validation, or transport-level IAM.

## Ranking Semantics

The default scorer is deterministic and lexical:

- title term matches are weighted highest
- tag term matches are weighted second
- body/content term matches are weighted third
- lineage matches add an extra relevance boost

If a query is provided, documents with a zero lexical score are excluded.

Tie-breaking order is:

1. total score descending
2. recency descending using `last_compiled`, then `last_updated`
3. title ascending
4. URI ascending

The SDK exposes scorer seams so future hybrid search can introduce BM25, vector
similarity, or LLM re-ranking without changing the repository interface.

## Lineage Semantics

The first implementation uses lineage as a deterministic filter and scoring
signal rather than a recursive graph walk. If `lineage_ids` are supplied, only
documents whose `lineage` intersects those identifiers are eligible. Matching
lineage also contributes to the score.

Recursive lineage expansion and graph traversal remain future enhancements.

## Briefing Assembly

Briefings are assembled from ranked documents in score order. Each section
includes:

- title
- doc_id
- URI
- document type
- visibility
- tags when present
- source list when present
- document body content

Token budgeting uses a deterministic character-based estimate. If the next full
section would exceed the remaining budget, the SDK emits a truncated final
section when possible and marks the result as truncated.

## Extension Points

The SDK is designed to evolve without contract churn:

- custom visibility policies can replace the default policy
- custom scorers can replace the lexical scorer
- future search adapters can feed the same retrieval and briefing models

## Out of Scope for This Contract

- vector database selection or runtime indexing requirements
- BM25 implementation details beyond extension points
- external identity providers, JWT validation, or API gateway auth
- recursive knowledge-graph traversal
- static-site or human-facing presentation concerns
