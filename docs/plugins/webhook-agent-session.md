# Webhook Agent Session

The agent-session webhook plugin is a first-party WayGate webhook integration for completed session transcript uploads.

It validates a structured completed-session payload, can verify HMAC signatures, stores the normalized session bundle as a raw artifact, and emits `draft.ready` so the existing compile workflow can process the transcript.

## What It Does

- Accepts completed session payloads from explicit upstream adapters.
- Verifies `X-Waygate-Timestamp` and `X-Waygate-Signature` when a signing secret is configured.
- Normalizes one uploaded session into one `RawDocument`.
- Stores the canonical transcript and metadata bundle in the raw artifact body as JSON.
- Emits `draft.ready` with a stable idempotency key and session metadata.

## Configuration

- `WAYGATE_AGENT_SESSION__SIGNING_SECRET`
- `WAYGATE_AGENT_SESSION__ALLOW_UNSIGNED`
- `WAYGATE_AGENT_SESSION__MAX_TIMESTAMP_SKEW_SECONDS`

## Helper Scripts

The repository ships helper utilities for building and posting completed session payloads:

- `scripts/build-agent-session-payload.py`
- `scripts/post-agent-session.py`
- `scripts/fixtures/agent-session.completed.json`

For a local smoke test, run the web app with `communication-http`, point it at `scripts/mock-worker.py`, and post the fixture payload through `scripts/post-agent-session.py`.

## Notes

- This plugin is intentionally a dedicated webhook plugin rather than an extension of the generic webhook plugin.
- It uses the existing compile trigger on purpose. Completed sessions become raw artifacts that feed the current compile workflow.
