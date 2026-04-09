# Apps

This page summarizes the top-level applications in `apps/` and links to key source files.

1. Compiler

- Purpose: Build and execute workflow graphs that transform and publish documents.
- Key files:
  - [apps/compiler README](apps/compiler/README.md)
  - [compiler config](apps/compiler/src/compiler/config.py)
  - [graph builder](apps/compiler/src/compiler/graph.py)
  - [compiler middleware / node spans](apps/compiler/src/compiler/middleware.py)
  - [worker/runner](apps/compiler/src/compiler/worker.py)
  - [maintenance sweep](apps/compiler/src/compiler/maintenance.py)
  - [state model](apps/compiler/src/compiler/state.py)
  - nodes: [draft](apps/compiler/src/compiler/nodes/draft.py), [review](apps/compiler/src/compiler/nodes/review.py), [publish](apps/compiler/src/compiler/nodes/publish.py)

1. Operator

- Purpose: Provide the human-facing Nuxt control plane and host the Better Auth backend on Postgres.
- Key files:
  - [apps/operator README](apps/operator/README.md)
  - [Nuxt config](apps/operator/nuxt.config.ts)
  - [Better Auth server config](apps/operator/lib/auth.ts)
  - [Better Auth client](apps/operator/lib/auth-client.ts)
  - [Better Auth server route](apps/operator/server/api/auth/[...all].ts)
  - [Landing page](apps/operator/app/pages/index.vue)
  - [Sign-in page](apps/operator/app/pages/sign-in.vue)
  - [Protected dashboard](apps/operator/app/pages/dashboard.vue)

1. Receiver

- Purpose: Accept ingestion inputs (HTTP webhooks, scheduled polls, listeners) and dispatch documents into storage/processing.
- Key files:
  - [apps/receiver README](apps/receiver/README.md)
  - [HTTP API](apps/receiver/src/receiver/api/webhooks.py)
  - [app entry](apps/receiver/src/receiver/app.py)
  - [poll scheduler](apps/receiver/src/receiver/core/scheduler.py)
  - [enqueue service](apps/receiver/src/receiver/services/trigger.py)

1. MCP Server

- Purpose: Provide the transport-facing briefing service layer on top of the retrieval SDK.
- Key files:
  - [apps/mcp_server README](apps/mcp_server/README.md)
  - [service boundary](apps/mcp_server/src/mcp_server/service.py)
  - [runtime config](apps/mcp_server/src/mcp_server/config.py)
  - [trace middleware](apps/mcp_server/src/mcp_server/trace.py)
  - [FastMCP server wrapper](apps/mcp_server/src/mcp_server/server.py)
  - [CLI entrypoint](apps/mcp_server/src/mcp_server/main.py)
