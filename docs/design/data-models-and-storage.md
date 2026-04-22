# Data Models and Storage

## Purpose

This document defines the main document contracts used in the current repository and explains how storage namespaces and document URIs behave.

## RawDocument: Canonical Ingestion Contract

Webhook plugins normalize external payloads into `RawDocument` objects from `waygate-core`.

Important fields:

| Field                                 | Meaning                                                                           |
| ------------------------------------- | --------------------------------------------------------------------------------- |
| `source_type`                         | Required source category identifier                                               |
| `source_id`                           | Optional provider-native identifier                                               |
| `source_uri`                          | Optional canonical URI for the source                                             |
| `source_hash`                         | Optional stable content hash                                                      |
| `content_type`                        | Optional canonical MIME type; inferred when omitted                               |
| `content_hash`                        | Internal body-only content hash used for storage and compile identity             |
| `source_metadata`                     | Provider-specific metadata object; must include `kind` and may include extra keys |
| `doc_id`                              | Generated UUIDv7 string by default                                                |
| `timestamp`                           | Required event or source timestamp                                                |
| `topics`, `tags`                      | Optional thematic labels                                                          |
| `people`, `organizations`, `projects` | Structured entity extraction fields                                               |
| `visibility`                          | Visibility classification                                                         |
| `content`                             | Raw body content                                                                  |

This model is the handoff boundary between webhook integrations and the rest of the system.

When `content_type` is supplied, raw-document handling canonicalizes it onto a MIME-style value such as `text/markdown`.

When `content_type` is omitted, raw-document rendering prefers the source filename extension from `source_uri` or `source_id` and falls back to body heuristics.

## Artifact-Specific Document Models

The current direction is to keep one explicit model per document artifact type instead of reusing `RawDocument` outside ingress.

- `RawDocument`: ingress-only source artifact produced by webhook plugins
- `DraftDocument`: validated compile-stage draft projected from workflow state before persistence
- `CompiledDocument`: approved durable compile artifact written to `compiled/`
- `PublishedDocument`: future corpus-level artifact intended for `published/`

`CompiledDocument` and `PublishedDocument` each have their own frontmatter model. Their metadata shapes are intentionally separate from `RawDocumentFrontmatter` so raw-only source fields do not leak into compiled or published artifacts.

## Raw Storage Artifact

The webhook ingress app does not store a `RawDocument` as JSON. It renders the model into a text artifact with frontmatter and writes that artifact to storage.

The compile workflow currently depends on these parsed fields when it reloads a raw artifact:

- `content`
- `content_type`
- `content_hash`
- `source_hash`
- `source_uri`
- `source_type`
- `timestamp`

That means raw-document rendering must continue to preserve those fields in frontmatter while leaving the stored body content unchanged.

The storage-facing identity for raw artifacts is now the internal `content_hash`.
It is computed from the normalized raw body content only and ignores frontmatter.
That lets raw storage deduplicate identical bodies even when provider metadata
differs.

## Compiled Document Contract

The compile workflow now writes one approved Markdown file per synthesized draft.

The implementation now treats that artifact as a `CompiledDocument` rendered through a dedicated compiled-document template in `waygate-core`.

Its frontmatter is generated from workflow state and currently includes:

- `doc_id`
- `source_set_key`
- `source_documents`
- `source_content_hashes`
- `source_hashes`
- `source_uris`
- `compiled_at`
- `review_feedback`
- aggregated `tags`
- aggregated `topics`
- aggregated `people`
- aggregated `organizations`
- aggregated `projects`

In the current implementation, `doc_id` is populated from the compiled draft
body hash, not from `source_set_key`.

The body of the compiled file is the synthesized Markdown draft.

The current repo therefore treats compiled markdown plus frontmatter as the
durable compile output.

Future retrieval, vector, or relational indexing work should treat this
compiled markdown artifact as the source of truth and build reconstructable
secondary indexes from it.

The later integration workflow will consume compiled artifacts and write
`published/<uuidv7>.md` documents after corpus-level merge and deduplication.

That future artifact should use the `PublishedDocument` contract and published-document renderer rather than reusing the compiled-document schema unchanged.

## Storage Namespaces

The storage contract is namespace-based.

`StorageNamespace` currently defines:

- `raw`
- `staging`
- `review`
- `compiled`
- `published`
- `metadata`
- `templates`
- `agents`

The first-party local storage plugin maps those namespaces to directories under a configurable base path.

Default layout:

```text
<base_path>/
  raw/
  staging/
  review/
  compiled/
  published/
  metadata/
  templates/
  agents/
```

## URI and Path Rules

The local storage plugin separates two concerns:

- namespaced filesystem paths used internally
- base-relative `file://` URIs returned from CRUD operations

Examples:

- a built raw path may normalize to `wiki/raw/<content-hash>.txt`
- the returned URI is base-relative, such as `file://raw/<content-hash>.txt`

This matters because producer and workflow code pass around the returned URIs, not absolute filesystem paths.

## Why Base-Relative URIs Matter

Base-relative URIs give storage plugins a stable handoff format that does not leak machine-specific absolute paths into workflow messages, tests, or persisted metadata.

That keeps three boundaries cleaner:

- web app and scheduler can hand work to workers without assuming a host path layout
- tests can assert storage behavior without depending on absolute directories
- future storage implementations can preserve the same high-level document reference shape even if the backing store changes

## Legacy Naming Differences

Some older docs used different directory names. The current repo uses these names instead:

| Legacy concept                   | Current namespace |
| -------------------------------- | ----------------- |
| `live`                           | `published`       |
| approved compile output          | `compiled`        |
| `meta/templates`                 | `templates`       |
| `meta/agents`                    | `agents`          |
| dead-letter or review draft area | `review`          |

Use the current namespace names in new work.

## Durable Source of Truth

The current repository design supports a simple rule:

- raw artifacts, review records, and compiled markdown are durable
- anything derived later from those artifacts should be rebuildable

That rule is already compatible with future retrieval, graph, or presentation layers, but those layers should remain downstream of the stored documents rather than becoming the primary system of record.

The same rule should apply to the planned multi-agent compile architecture. Future checkpointed workflow state may carry durable compile progress, and transient prompt context may be reconstructed per document pass, but neither of those should replace raw, review, or published artifacts as the durable product boundary of the system.
