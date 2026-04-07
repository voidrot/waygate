# mcp_server

Thin briefing service layer for WayGate.

This app wraps `waygate_agent_sdk` and is intended to become the transport-facing
surface for MCP tool exposure. The current implementation keeps the boundary
small: generate a token-budgeted briefing and preview ranked retrieval results
without bypassing the SDK.

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
