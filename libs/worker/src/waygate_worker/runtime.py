from __future__ import annotations

import asyncio

from waygate_core import bootstrap_app
from waygate_core.plugin import WorkflowTriggerRunner
from waygate_core.plugin import resolve_communication_worker_transport
from waygate_workflows.router import process_workflow_trigger
from waygate_workflows.runtime import validate_compile_llm_readiness


async def run_worker(
    preferred_plugin_name: str | None = None,
    *,
    runner: WorkflowTriggerRunner = process_workflow_trigger,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Run the worker transport selected by config or an explicit override."""

    app_context = bootstrap_app()
    validate_compile_llm_readiness()
    transport_name = (
        preferred_plugin_name or app_context.config.core.communication_plugin_name
    )
    transport = resolve_communication_worker_transport(
        app_context.plugins.communication_workers,
        transport_name,
        allow_fallback=False,
    )
    await transport.run(runner, stop_event=stop_event)
