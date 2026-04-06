# Local Storage Plugin

Provides a `StorageProvider` implementation that stores raw and live documents
on the local filesystem under a configurable base directory.

Key file:

- [local_storage.py](plugins/storage_local/src/waygate_plugin_local_storage/local_storage.py)

Configuration:

- `LOCAL_STORAGE_PATH` environment variable (default: `wiki`) controls the base directory. The plugin creates `raw/` and `live/` subdirectories.

Usage:

- The provider exposes methods to write/read/list/delete raw and live documents and returns file:// URIs for stored items.
