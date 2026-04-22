# waygate-workflows

Shared workflow entrypoints for WayGate.

This package hosts importable workflow functions that can be executed by worker
runtimes such as RQ. Keeping workflow code here lets producer processes enqueue
jobs by string reference while worker processes import and execute the same code.

## Current scope

- `waygate_workflows.draft.jobs.process_workflow_trigger` handles queued
  `WorkflowTriggerMessage` payloads.
- `draft.ready` currently hands through already-written draft document URIs as
  the minimal boundary for the future draft workflow.

## Package layout

- `waygate_workflows.tools` is reserved for LangChain-callable tools used by
   workflow agents.
- `waygate_workflows.runtime` contains provider resolution, storage
   resolution, checkpoint wiring, and other runtime-facing helpers.
- `waygate_workflows.content` contains source-document parsing, guidance
   loading, and publish-artifact rendering helpers.

## LLM Workflow Profiles

Workflow execution still resolves models through the active LLM provider plugin.
For Ollama-backed runs, keep the configuration layers separate:

- `WAYGATE_CORE__LLM_PLUGIN_NAME=OllamaProvider`
- `WAYGATE_OLLAMAPROVIDER__BASE_URL=http://localhost:11434`
- `WAYGATE_CORE__LLM_WORKFLOW_PROFILES='<json>'`

The preferred per-role tuning shape for compile is the JSON object below.
Legacy stage-model env vars such as `WAYGATE_CORE__METADATA_MODEL_NAME`,
`WAYGATE_CORE__DRAFT_MODEL_NAME`, and `WAYGATE_CORE__REVIEW_MODEL_NAME`
remain valid fallbacks.

The runtime validates every resolved LLM request before execution. In strict
mode, unsupported options and missing structured-output capability raise
`LLMConfigurationError`, and the worker router returns a `failed` result with
`error_kind = config` instead of attempting a partial run.

The draft worker also preflights the active provider at startup. Providers can
optionally implement the `LLMReadinessProbe` companion contract for a dedicated
readiness check; otherwise the workflow layer falls back to constructing the
compile workflow's configured stage clients. This catches missing credentials,
invalid provider options, and provider-construction failures before the worker
begins polling for jobs.

```json
{
   "compile": {
      "common_options": {
         "temperature": 0.1
      },
      "provider_options": {
         "OllamaProvider": {
            "num_ctx": 8192
         }
      },
      "option_policy": "strict"
   },
   "compile.source-analysis.metadata": {
      "model_name": "qwen3.5:9b",
      "common_options": {
         "temperature": 0.0
      },
      "provider_options": {
         "OllamaProvider": {
            "num_ctx": 4096
         }
      }
   },
   "compile.source-analysis.summary": {
      "model_name": "qwen3.5:9b",
      "common_options": {
         "temperature": 0.2
      },
      "provider_options": {
         "OllamaProvider": {
            "num_ctx": 8192
         }
      }
   },
   "compile.source-analysis.findings": {
      "model_name": "qwen3.5:9b",
      "common_options": {
         "temperature": 0.0
      },
      "provider_options": {
         "OllamaProvider": {
            "num_ctx": 8192
         }
      }
   },
   "compile.source-analysis.continuity": {
      "model_name": "qwen3.5:9b",
      "common_options": {
         "temperature": 0.0
      },
      "provider_options": {
         "OllamaProvider": {
            "num_ctx": 8192
         }
      }
   },
   "compile.source-analysis.supervisor": {
      "model_name": "qwen3.5:9b",
      "common_options": {
         "temperature": 0.1
      },
      "provider_options": {
         "OllamaProvider": {
            "num_ctx": 8192
         }
      }
   },
   "compile.synthesis": {
      "model_name": "qwen3.5:9b",
      "common_options": {
         "temperature": 0.4
      },
      "provider_options": {
         "OllamaProvider": {
            "num_ctx": 16384,
            "num_predict": 1200
         }
      }
   },
   "compile.review": {
      "model_name": "hermes3:8b",
      "common_options": {
         "temperature": 0.0
      },
      "provider_options": {
         "OllamaProvider": {
            "num_ctx": 8192
         }
      }
   }
}
```
