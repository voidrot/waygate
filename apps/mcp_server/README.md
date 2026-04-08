# mcp_server

Thin briefing service layer for WayGate.

This app wraps `waygate_agent_sdk` and is intended to become the transport-facing
surface for MCP tool exposure. The current implementation keeps the boundary
small: generate a token-budgeted briefing, preview ranked retrieval results,
and persist explicit context-gap reports without bypassing the SDK and storage
boundaries.

The server uses the official MCP Python SDK via `mcp.server.fastmcp.FastMCP`.

Run it directly with:

- `uv run waygate-mcp-server`
- `python -m mcp_server`

For local development with reload:

- `mise run mcp:dev`

Relevant environment variables:

- `MCP_SERVER_HOST` default `127.0.0.1`
- `MCP_SERVER_PORT` default `8000`
- `MCP_SERVER_PATH` default `/mcp`
- `MCP_AUTH_ENABLED` default `false`
- `MCP_AUTH_TOKEN` required when auth is enabled
- `MCP_DEFAULT_ROLE` optional server-side role override for retrieval scope mapping
- `MCP_ALLOWED_VISIBILITIES` comma-separated server-side visibility allowlist, default `public,internal`

Trace propagation:

- HTTP requests can send `X-Trace-Id`; if omitted, the server generates one.
- The response echoes `X-Trace-Id`.
- MCP retrieval audit events reuse the current trace id.

Available tools:

- `generate_briefing`
- `preview_retrieval`
- `report_context_error` for persisting a durable `meta/maintenance` artifact when a caller detects missing context. When lineage anchors are supplied, the stored artifact also carries a recompilation signal that the maintenance sweep can replay into the compiler queue.
