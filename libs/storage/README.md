# WayGate Storage

`libs/storage` defines storage provider interfaces and the registry used to
discover concrete storage implementations.

Key files:

- [storage_base.py](libs/storage/src/waygate_storage/storage_base.py) — base `StorageProvider` interface.
- [storage_registry.py](libs/storage/src/waygate_storage/storage_registry.py) — discovery and selection of storage providers.

Usage

Providers implement the `StorageProvider` interface and are discovered via
entry points. See `plugins/storage_local` for a local filesystem example.
