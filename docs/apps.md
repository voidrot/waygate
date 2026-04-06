# Apps

This page summarizes the top-level applications in `apps/` and links to key source files.

1. Compiler

- Purpose: Build and execute workflow graphs that transform and publish documents.
- Key files:
  - [apps/compiler README](apps/compiler/README.md)
  - [compiler config](apps/compiler/src/compiler/config.py)
  - [graph builder](apps/compiler/src/compiler/graph.py)
  - [worker/runner](apps/compiler/src/compiler/worker.py)
  - [state model](apps/compiler/src/compiler/state.py)
  - nodes: [draft](apps/compiler/src/compiler/nodes/draft.py), [review](apps/compiler/src/compiler/nodes/review.py), [publish](apps/compiler/src/compiler/nodes/publish.py)

1. Receiver

- Purpose: Accept ingestion inputs (HTTP webhooks, scheduled polls, listeners) and dispatch documents into storage/processing.
- Key files:
  - [apps/receiver README](apps/receiver/README.md)
  - [HTTP API](apps/receiver/src/receiver/api/webhooks.py)
  - [health endpoint](apps/receiver/src/receiver/api/health.py)
  - [app entry](apps/receiver/src/receiver/app.py)
  - [clients and services](apps/receiver/src/receiver/clients, apps/receiver/src/receiver/services)
