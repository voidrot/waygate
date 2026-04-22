# LLM Provider Follow-Up Plan

## Purpose

This document captures the remaining follow-up work after the Ollama provider completeness review, the provider readiness work, and the optional embeddings extension.

This is a planning document, not the source of truth for current runtime behavior. For the implemented contracts and current system behavior, use:

- [docs/design/runtime-and-plugins.md](../design/runtime-and-plugins.md)
- [docs/design/architecture.md](../design/architecture.md)
- [docs/design/ingestion-and-workflows.md](../design/ingestion-and-workflows.md)

## Status

The original provider-hardening work is complete.

Completed work includes:

- provider-side readiness validation through an optional companion contract
- startup preflight for compile-stage LLM usage in worker startup
- improved provider-construction error wrapping in workflow helpers
- Ollama and Featherless provider hardening within the shared LLM contract
- optional embeddings support through a separate companion contract
- provider, workflow, and documentation updates for the embeddings path

Remaining work is now narrower and falls into three buckets:

- real-environment verification against a live Ollama instance
- additional optional provider extensions, if they are still worth adopting
- an actual in-repo consumer for the new embeddings path

## Remaining Work

### 1. Live Ollama smoke validation

Run a real smoke path against a reachable Ollama server with the configured metadata, draft, and review models available locally.

This should verify:

- startup readiness behavior against a live server
- the default `validate_model_on_init` behavior
- real text-generation and structured-output invocation behavior
- the operational assumptions documented for the Ollama provider

This remains open because the current environment has not had a reachable Ollama server on the default local endpoint.

### 2. Decide the next optional provider extension

The next phase-2 extension should still follow the same rule used for readiness and embeddings: keep `LLMProviderPlugin` minimal and add only optional or companion interfaces where they are broadly useful.

Current candidates are:

1. Provider operations or model catalog
2. Streaming responses
3. Token counting or token estimation

Provider operations or model catalog is the most natural next candidate if the goal is operational completeness, because it can support health, diagnostics, and future admin tooling without changing the text-generation call surface.

Streaming is reasonable only if there is a real consumer ready to use streamed output. Token counting is useful, but it is less urgent unless there is an active budgeting or chunking requirement in the workflow layer.

### 3. Add an actual embeddings consumer

The optional embeddings contract now exists, but the repository does not yet include a retrieval-oriented workflow, service, or helper that uses it end to end.

The next concrete embeddings consumer should:

- resolve embeddings through the active provider rather than constructing provider SDK clients directly
- use an explicit embedding model name rather than reusing compile-stage generation model defaults
- fail clearly when the configured provider does not implement the embeddings companion contract

This is the cleanest way to prove the new contract is useful beyond provider-level construction tests.

## Suggested Order

If this work resumes later, the recommended order is:

1. Perform live Ollama smoke validation.
2. Decide whether the next optional provider extension is still needed.
3. If embeddings are the next near-term product need, add an actual embeddings consumer before widening the provider surface again.
4. If operational tooling is the next need, implement provider operations or model catalog as the next companion interface.

## Verification

When this work resumes, verify it with:

1. Provider unit tests for any new optional interface.
2. Workflow or consumer-level tests for any new helper or integration path.
3. A live Ollama smoke run against a real server for any claim about operational completeness.
4. Documentation checks to keep provider docs and design docs aligned with the implemented boundary.

## Relevant Files

- `/home/buck/src/voidrot/waygate/libs/core/src/waygate_core/plugin/llm.py`
- `/home/buck/src/voidrot/waygate/libs/workflows/src/waygate_workflows/runtime/llm.py`
- `/home/buck/src/voidrot/waygate/plugins/provider-ollama/src/waygate_plugin_provider_ollama/plugin.py`
- `/home/buck/src/voidrot/waygate/plugins/provider-featherless-ai/src/waygate_plugin_provider_featherless_ai/plugin.py`
- `/home/buck/src/voidrot/waygate/plugins/provider-ollama/README.md`
- `/home/buck/src/voidrot/waygate/plugins/provider-featherless-ai/README.md`
- `/home/buck/src/voidrot/waygate/docs/plugins/provider-ollama.md`
- `/home/buck/src/voidrot/waygate/docs/plugins/provider-featherless-ai.md`

## Decision Record

- Keep the base `LLMProviderPlugin` contract narrow.
- Prefer companion interfaces over optional methods on the base provider when the feature is not universal.
- Treat live-provider smoke validation as the remaining requirement for claiming real operational completeness.
- Do not add more provider surface area unless there is a concrete consumer or operational reason for it.
