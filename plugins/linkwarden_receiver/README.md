# Linkwarden Receiver Plugin

Ingestion plugin targeted at Linkwarden links/bookmarks. It runs in poll mode
against Linkwarden's API and normalizes links into canonical `RawDocument`
records with enriched web metadata.

Mode support

- `poll`: supported
- `handle_webhook`: not supported

Environment variables

- `LINKWARDEN_BASE_URL` (required), for example `https://linkwarden.example.com`
- `LINKWARDEN_TOKEN` (required), bearer token used for API calls
- `LINKWARDEN_SORT` (optional, default `0`)
- `LINKWARDEN_SEARCH_QUERY` (optional)
- `LINKWARDEN_COLLECTION_ID` (optional)
- `LINKWARDEN_TAG_ID` (optional)
- `LINKWARDEN_PINNED_ONLY` (optional)

Polling uses `GET /api/v1/search` with bearer authentication.

Key file:

- [webhook_receiver.py](plugins/linkwarden_receiver/src/waygate_plugin_linkwarden_receiver/webhook_receiver.py)
