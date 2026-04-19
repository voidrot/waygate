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
| `source_metadata`                     | Provider-specific metadata object; must include `kind` and may include extra keys |
| `doc_id`                              | Generated UUIDv7 string by default                                                |
| `timestamp`                           | Required event or source timestamp                                                |
| `topics`, `tags`                      | Optional thematic labels                                                          |
| `people`, `organizations`, `projects` | Structured entity extraction fields                                               |
| `visibility`                          | Visibility classification                                                         |
| `content`                             | Raw body content                                                                  |

This model is the handoff boundary between webhook integrations and the rest of the system.

## Raw Storage Artifact

The API does not store a `RawDocument` as JSON. It renders the model into a text artifact with frontmatter and writes that artifact to storage.

The compile workflow currently depends on these parsed fields when it reloads a raw artifact:

- `content`
- `source_hash`
- `source_uri`
- `source_type`
- `timestamp`

That means raw-document rendering must continue to preserve those fields in frontmatter.

## Published Document Contract

The current publish step writes one Markdown file per source set.

Its frontmatter is generated from workflow state and currently includes:

- `doc_id`
- `source_set_key`
- `source_documents`
- `source_hashes`
- `source_uris`
- `compiled_at`
- `review_feedback`
- aggregated `tags`
- aggregated `topics`
- aggregated `people`
- aggregated `organizations`
- aggregated `projects`

In the current implementation, `doc_id` is populated from the derived `source_set_key`. The older compile plan assumed a separate UUIDv7 publish identifier, but that is not how the current workflow publishes artifacts today.

The body of the published file is the synthesized Markdown draft.

The current repo therefore treats published markdown plus frontmatter as the durable compile output.

Future retrieval, vector, or relational indexing work should treat this published markdown artifact as the source of truth and build reconstructable secondary indexes from it.

## Storage Namespaces

The storage contract is namespace-based.

`StorageNamespace` currently defines:

- `raw`
- `staging`
- `review`
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

- a built raw path may normalize to `wiki/raw/<id>.txt`
- the returned URI is base-relative, such as `file://raw/<id>.txt`

This matters because producer and workflow code pass around the returned URIs, not absolute filesystem paths.

## Why Base-Relative URIs Matter

Base-relative URIs give storage plugins a stable handoff format that does not leak machine-specific absolute paths into workflow messages, tests, or persisted metadata.

That keeps three boundaries cleaner:

- API and scheduler can hand work to workers without assuming a host path layout
- tests can assert storage behavior without depending on absolute directories
- future storage implementations can preserve the same high-level document reference shape even if the backing store changes

## Legacy Naming Differences

Some older docs used different directory names. The current repo uses these names instead:

| Legacy concept                   | Current namespace |
| -------------------------------- | ----------------- |
| `live`                           | `published`       |
| `meta/templates`                 | `templates`       |
| `meta/agents`                    | `agents`          |
| dead-letter or review draft area | `review`          |

Use the current namespace names in new work.

## Durable Source of Truth

The current repository design supports a simple rule:

- raw artifacts, review records, and published markdown are durable
- anything derived later from those artifacts should be rebuildable

That rule is already compatible with future retrieval, graph, or presentation layers, but those layers should remain downstream of the stored documents rather than becoming the primary system of record.

The same rule should apply to the planned multi-agent compile architecture. Future checkpointed workflow state may carry durable compile progress, and transient prompt context may be reconstructed per document pass, but neither of those should replace raw, review, or published artifacts as the durable product boundary of the system.
