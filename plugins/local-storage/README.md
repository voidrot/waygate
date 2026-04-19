# waygate-plugin-local-storage

WayGate storage plugin backed by the local filesystem. Organises documents into a conventional directory structure under a configurable base path.

## Directory Layout

```
<base_path>/
  raw/        — incoming documents before processing
  staging/    — drafts in progress
  review/     — documents awaiting human review
  published/  — published documents
  metadata/   — document metadata files
  templates/  — document templates
  agents/     — agent configuration files
```

## Installation

```bash
uv add waygate-plugin-local-storage
```

The plugin is discovered automatically via its entry point. No code changes are required.

## Configuration

All settings are read from environment variables under `WAYGATE_LOCAL_STORAGE__*`:

| Variable | Default | Description |
|---|---|---|
| `WAYGATE_LOCAL_STORAGE__BASE_PATH` | `wiki` | Root directory for all storage |
| `WAYGATE_LOCAL_STORAGE__FILE_PREFIX` | `file://` | URI prefix used for returned document paths |
| `WAYGATE_LOCAL_STORAGE__RAW_DIR` | `raw` | Subdirectory for raw input |
| `WAYGATE_LOCAL_STORAGE__STAGING_DIR` | `staging` | Subdirectory for staging drafts |
| `WAYGATE_LOCAL_STORAGE__REVIEW_DIR` | `review` | Subdirectory for review queue |
| `WAYGATE_LOCAL_STORAGE__PUBLISH_DIR` | `published` | Subdirectory for published docs |
| `WAYGATE_LOCAL_STORAGE__METADATA_DIR` | `metadata` | Subdirectory for metadata |
| `WAYGATE_LOCAL_STORAGE__TEMPLATES_DIR` | `templates` | Subdirectory for templates |
| `WAYGATE_LOCAL_STORAGE__AGENTS_DIR` | `agents` | Subdirectory for agent configs |
| `WAYGATE_LOCAL_STORAGE__SOFT_DELETE` | `false` | Move to trash instead of deleting |
| `WAYGATE_LOCAL_STORAGE__KEEP_VERSIONED` | `false` | Keep timestamped versions when files are updated/deleted |

## Entry Point

```toml
[project.entry-points."waygate.plugins.storage"]
local_storage = "waygate_plugin_local_storage.plugin:LocalStoragePlugin"
```
