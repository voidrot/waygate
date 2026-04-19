# Generic Webhook Plugin

The generic webhook plugin is the reference implementation for inbound webhook ingestion in WayGate.

It validates a structured JSON payload, converts each payload document into a `RawDocument`, and exposes an OpenAPI payload schema so the API can document the request body correctly.

## What It Does

- Reads its plugin registration from the webhook plugin entry point group.
- Validates payloads against Pydantic models.
- Merges top-level and per-document topics and tags with stable first-seen ordering.
- Normalizes webhook timestamps to UTC.
- Returns a list of `RawDocument` objects for the API route to store.

## Behavior

- Verification is permissive by default and intended to be overridden for production signature checks.
- `originated_at` is optional and falls back to the current UTC time.
- `originated_at` must include timezone information when provided.
- Invalid payloads and invalid document metadata raise `ValueError`.

## Payload Shape

The plugin expects a payload with a top-level `metadata` object and a `documents` array.

The included README contains the concrete example payload shape used by the tests and the current API route.

## Configuration

This plugin does not currently define config fields, but it still participates in the shared plugin config registration flow.

## Entry Point

- `waygate.plugins.webhooks`

## Notes

- This plugin is a reference implementation for custom webhook adapters.
- It is the webhook plugin used by the current API route and OpenAPI schema merging logic.
# Generic Webhook Plugin

The generic webhook plugin is the reference implementation for inbound webhook ingestion in WayGate.

It validates a structured JSON payload, converts each payload document into a `RawDocument`, and exposes an OpenAPI payload schema so the API can document the request body correctly.

## What It Does

- Reads its plugin registration from the webhook plugin entry point group.
- Validates payloads against Pydantic models.
- Merges top-level and per-document topics and tags with stable first-seen ordering.
- Normalizes webhook timestamps to UTC.
- Returns a list of `RawDocument` objects for the API route to store.

## Behavior

- Verification is permissive by default and intended to be overridden for production signature checks.
- `originated_at` is optional and falls back to the current UTC time.
- `originated_at` must include timezone information when provided.
- Invalid payloads and invalid document metadata raise `ValueError`.

## Payload Shape

The plugin expects a payload with a top-level `metadata` object and a `documents` array.

The included README contains the concrete example payload shape used by the tests and the current API route.

## Configuration

This plugin does not currently define config fields, but it still participates in the shared plugin config registration flow.

## Entry Point

- `waygate.plugins.webhooks`

## Notes

- This plugin is a reference implementation for custom webhook adapters.
- It is the webhook plugin used by the current API route and OpenAPI schema merging logic.
