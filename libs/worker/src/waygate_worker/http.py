from __future__ import annotations

import asyncio
import contextlib
import hmac
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field
import uvicorn

from waygate_core.logging import get_logger
from waygate_core.plugin import WorkflowTriggerMessage, WorkflowTriggerRunner

logger = get_logger(__name__)


class HTTPWorkerConfig(BaseModel):
    """Configuration for the HTTP worker transport runtime."""

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8090, ge=1, le=65535)
    endpoint_path: str = Field(default="/workflows/trigger")
    auth_token: str | None = Field(default=None)
    auth_header: str = Field(default="Authorization")


def build_http_worker_app(
    config: HTTPWorkerConfig,
    *,
    runner: WorkflowTriggerRunner,
) -> FastAPI:
    """Build the HTTP worker app for accepting workflow trigger requests."""

    app = FastAPI(title="WayGate Worker", version="0.1.0")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(config.endpoint_path, status_code=status.HTTP_202_ACCEPTED)
    async def trigger_workflow(
        message: WorkflowTriggerMessage,
        background_tasks: BackgroundTasks,
        request: Request,
    ) -> dict[str, str]:
        _verify_http_auth(config, request)
        message_id = _build_http_message_id(message)
        payload = message.model_dump(mode="json")
        background_tasks.add_task(
            _execute_workflow_trigger,
            runner,
            payload,
            message_id=message_id,
        )
        return {"status": "accepted", "message_id": message_id}

    return app


async def run_http_worker(
    config: HTTPWorkerConfig,
    *,
    runner: WorkflowTriggerRunner,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Serve the HTTP worker endpoint until shutdown."""

    app = build_http_worker_app(config, runner=runner)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=config.host,
            port=config.port,
            log_level="info",
            access_log=False,
        )
    )
    stop_task: asyncio.Task[None] | None = None
    if stop_event is not None:
        stop_task = asyncio.create_task(_watch_for_stop(stop_event, server))

    try:
        await server.serve()
    finally:
        if stop_task is not None:
            stop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await stop_task


async def _watch_for_stop(stop_event: asyncio.Event, server: uvicorn.Server) -> None:
    await stop_event.wait()
    server.should_exit = True


async def _execute_workflow_trigger(
    runner: WorkflowTriggerRunner,
    payload: dict[str, object],
    *,
    message_id: str,
) -> None:
    try:
        result = await asyncio.to_thread(runner, payload)
    except Exception as exc:
        logger.error(
            "HTTP worker trigger execution raised",
            message_id=message_id,
            detail=str(exc),
        )
        return

    logger.info(
        "HTTP worker trigger completed",
        message_id=message_id,
        status=result.get("status", "unknown"),
        error_kind=result.get("error_kind"),
    )


def _verify_http_auth(config: HTTPWorkerConfig, request: Request) -> None:
    if not config.auth_token:
        return

    header_value = request.headers.get(config.auth_header)
    if header_value is None or not hmac.compare_digest(header_value, config.auth_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


def _build_http_message_id(message: WorkflowTriggerMessage) -> str:
    if message.idempotency_key:
        return f"{message.event_type}:{message.idempotency_key}"
    return str(uuid4())
