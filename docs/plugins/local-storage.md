# Local Storage Plugin

The local storage plugin is the filesystem-backed storage implementation for WayGate.

It organizes documents into named namespaces below a configurable base directory and returns base-relative `file://` URIs when documents are written, listed, or read through storage paths.

## What It Does

- Reads configuration from `WAYGATE_LOCAL_STORAGE__*` variables.
- Creates the directory structure needed for the configured namespaces.
- Builds namespaced storage paths for raw, staging, review, published, metadata, templates, and agents content.
- Writes, reads, lists, and deletes documents on the local filesystem.

## Behavior

- Returned document references are base-relative `file://` URIs.
- Existing namespace prefixes are normalized away when building namespaced paths.
- Optional soft delete and versioned file retention are supported.

## Configuration

| Variable                                | Default     | Description                                                 |
| --------------------------------------- | ----------- | ----------------------------------------------------------- |
| `WAYGATE_LOCAL_STORAGE__BASE_PATH`      | `wiki`      | Root directory for all storage namespaces.                  |
| `WAYGATE_LOCAL_STORAGE__FILE_PREFIX`    | `file://`   | URI prefix used for returned document paths.                |
| `WAYGATE_LOCAL_STORAGE__RAW_DIR`        | `raw`       | Subdirectory for raw input.                                 |
| `WAYGATE_LOCAL_STORAGE__STAGING_DIR`    | `staging`   | Subdirectory for in-progress drafts.                        |
| `WAYGATE_LOCAL_STORAGE__REVIEW_DIR`     | `review`    | Subdirectory for review artifacts.                          |
| `WAYGATE_LOCAL_STORAGE__PUBLISH_DIR`    | `published` | Subdirectory for published documents.                       |
| `WAYGATE_LOCAL_STORAGE__METADATA_DIR`   | `metadata`  | Subdirectory for metadata files.                            |
| `WAYGATE_LOCAL_STORAGE__TEMPLATES_DIR`  | `templates` | Subdirectory for templates.                                 |
| `WAYGATE_LOCAL_STORAGE__AGENTS_DIR`     | `agents`    | Subdirectory for agent files.                               |
| `WAYGATE_LOCAL_STORAGE__SOFT_DELETE`    | `false`     | Enables move-to-deleted behavior instead of hard delete.    |
| `WAYGATE_LOCAL_STORAGE__KEEP_VERSIONED` | `false`     | Keeps timestamped copies when files are updated or deleted. |

## Entry Point

- `waygate.plugins.storage`

## Notes

- This plugin is the current durable storage backend for raw, review, and published artifacts.
- Callers should pass trusted path strings because the plugin does not attempt to be a sandboxing layer.
# Local Storage Plugin

The local storage plugin is the filesystem-backed storage implementation for WayGate.

It organizes documents into named namespaces below a configurable base directory and returns base-relative `file://` URIs when documents are written, listed, or read through storage paths.

## What It Does

- Reads configuration from `WAYGATE_LOCAL_STORAGE__*` variables.
- Creates the directory structure needed for the configured namespaces.
- Builds namespaced storage paths for raw, staging, review, published, metadata, templates, and agents content.
- Writes, reads, lists, and deletes documents on the local filesystem.

## Behavior

- Returned document references are base-relative `file://` URIs.
- Existing namespace prefixes are normalized away when building namespaced paths.
- Optional soft delete and versioned file retention are supported.

## Configuration

| Variable                                | Default     | Description                                                 |
| --------------------------------------- | ----------- | ----------------------------------------------------------- |
| `WAYGATE_LOCAL_STORAGE__BASE_PATH`      | `wiki`      | Root directory for all storage namespaces.                  |
| `WAYGATE_LOCAL_STORAGE__FILE_PREFIX`    | `file://`   | URI prefix used for returned document paths.                |
| `WAYGATE_LOCAL_STORAGE__RAW_DIR`        | `raw`       | Subdirectory for raw input.                                 |
| `WAYGATE_LOCAL_STORAGE__STAGING_DIR`    | `staging`   | Subdirectory for in-progress drafts.                        |
| `WAYGATE_LOCAL_STORAGE__REVIEW_DIR`     | `review`    | Subdirectory for review artifacts.                          |
| `WAYGATE_LOCAL_STORAGE__PUBLISH_DIR`    | `published` | Subdirectory for published documents.                       |
| `WAYGATE_LOCAL_STORAGE__METADATA_DIR`   | `metadata`  | Subdirectory for metadata files.                            |
| `WAYGATE_LOCAL_STORAGE__TEMPLATES_DIR`  | `templates` | Subdirectory for templates.                                 |
| `WAYGATE_LOCAL_STORAGE__AGENTS_DIR`     | `agents`    | Subdirectory for agent files.                               |
| `WAYGATE_LOCAL_STORAGE__SOFT_DELETE`    | `false`     | Enables move-to-deleted behavior instead of hard delete.    |
| `WAYGATE_LOCAL_STORAGE__KEEP_VERSIONED` | `false`     | Keeps timestamped copies when files are updated or deleted. |

## Entry Point

- `waygate.plugins.storage`

## Notes

- This plugin is the current durable storage backend for raw, review, and published artifacts.
- Callers should pass trusted path strings because the plugin does not attempt to be a sandboxing layer.
