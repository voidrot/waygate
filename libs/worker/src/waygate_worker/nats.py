from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Annotated, Any, Protocol

import nats
from nats.errors import ConnectionClosedError, NoServersError, TimeoutError
from nats.js.api import AckPolicy, ConsumerConfig, StorageType, StreamConfig
from nats.js.errors import FetchTimeoutError
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from waygate_core import bootstrap_app
from waygate_core.logging import get_logger
from waygate_core.plugin import DispatchErrorKind
from waygate_workflows.router import process_workflow_trigger
from waygate_workflows.runtime import validate_compile_llm_readiness

logger = get_logger(__name__)

_TERMINAL_ERROR_KINDS = {
    DispatchErrorKind.CONFIG.value,
    DispatchErrorKind.PERMANENT.value,
    DispatchErrorKind.VALIDATION.value,
}


class WorkflowTriggerRunner(Protocol):
    def __call__(self, payload: dict[str, object] | str) -> dict[str, object]: ...


class NatsWorkerConfig(BaseSettings):
    """Configuration for the JetStream-backed worker runtime."""

    model_config = SettingsConfigDict(
        env_prefix="WAYGATE_WORKER__",
        env_file=".env",
        extra="ignore",
    )

    servers: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["nats://localhost:4222"]
    )
    stream_name: str = Field(default="WAYGATE_WORKFLOW")
    draft_subject: str = Field(default="waygate.workflow.draft")
    cron_subject: str = Field(default="waygate.workflow.cron")
    draft_consumer_name: str = Field(default="waygate-draft")
    cron_consumer_name: str = Field(default="waygate-cron")
    client_name: str = Field(default="waygate-nats-worker")
    connect_timeout_seconds: float = Field(default=2.0, gt=0)
    js_api_timeout_seconds: float = Field(default=5.0, gt=0)
    fetch_batch_size: int = Field(default=1, ge=1)
    fetch_timeout_seconds: float = Field(default=5.0, gt=0)
    fetch_heartbeat_seconds: float = Field(default=1.0, gt=0)
    idle_sleep_seconds: float = Field(default=1.0, ge=0)
    in_progress_heartbeat_seconds: float = Field(default=15.0, gt=0)
    ack_wait_seconds: float = Field(default=30.0, gt=0)
    max_deliver: int = Field(default=3, ge=1)
    max_ack_pending: int = Field(default=1, ge=1)
    backoff_seconds: Annotated[list[float], NoDecode] = Field(
        default_factory=lambda: [10.0, 30.0, 60.0]
    )
    duplicate_window_seconds: float = Field(default=120.0, gt=0)

    @field_validator("servers", mode="before")
    @classmethod
    def _normalize_servers(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("servers must be a list[str] or comma-delimited string")

    @field_validator("backoff_seconds", mode="before")
    @classmethod
    def _normalize_backoff(cls, value: object) -> list[float]:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                decoded = json.loads(stripped)
                return [float(item) for item in decoded]
            return [float(item.strip()) for item in stripped.split(",") if item.strip()]
        if isinstance(value, list):
            return [float(item) for item in value]
        raise TypeError("backoff_seconds must be a list[float] or string")


async def _run_sync_with_heartbeats(
    runner: WorkflowTriggerRunner,
    payload: dict[str, object],
    *,
    heartbeat_interval: float,
    in_progress: Callable[[], Any] | None,
) -> dict[str, object]:
    """Run the blocking workflow in a thread while sending in-progress acks."""

    if in_progress is None:
        return await asyncio.to_thread(runner, payload)

    task = asyncio.create_task(asyncio.to_thread(runner, payload))
    while True:
        try:
            return await asyncio.wait_for(
                asyncio.shield(task), timeout=heartbeat_interval
            )
        except asyncio.TimeoutError:
            await in_progress()


def _consumer_config(config: NatsWorkerConfig, subject: str) -> ConsumerConfig:
    return ConsumerConfig(
        durable_name=(
            config.draft_consumer_name
            if subject == config.draft_subject
            else config.cron_consumer_name
        ),
        filter_subject=subject,
        ack_policy=AckPolicy.EXPLICIT,
        ack_wait=config.ack_wait_seconds,
        max_deliver=config.max_deliver,
        backoff=config.backoff_seconds,
        max_ack_pending=config.max_ack_pending,
    )


async def _ensure_stream(nc, config: NatsWorkerConfig) -> None:
    """Ensure the JetStream stream exists with the configured subjects."""

    jetstream = nc.jetstream(timeout=config.js_api_timeout_seconds)
    stream_config = StreamConfig(
        name=config.stream_name,
        subjects=[config.draft_subject, config.cron_subject],
        storage=StorageType.FILE,
        duplicate_window=config.duplicate_window_seconds,
    )
    try:
        info = await jetstream.stream_info(config.stream_name)
    except Exception as exc:
        status_code = getattr(exc, "code", None)
        if status_code != 404:
            raise
        await jetstream.add_stream(config=stream_config)
        return

    existing_subjects = set(info.config.subjects or [])
    desired_subjects = set(stream_config.subjects or [])
    if (
        existing_subjects != desired_subjects
        or getattr(info.config, "duplicate_window", None)
        != config.duplicate_window_seconds
    ):
        await jetstream.update_stream(config=stream_config)


async def process_jetstream_message(
    message,
    *,
    runner: WorkflowTriggerRunner = process_workflow_trigger,
    heartbeat_interval: float = 15.0,
) -> dict[str, object]:
    """Decode, execute, and settle one JetStream message."""

    try:
        payload = json.loads(message.data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.error("Rejecting invalid JetStream payload", detail=str(exc))
        await message.term()
        return {
            "status": "failed",
            "error_kind": DispatchErrorKind.VALIDATION.value,
            "detail": str(exc),
        }

    try:
        result = await _run_sync_with_heartbeats(
            runner,
            payload,
            heartbeat_interval=heartbeat_interval,
            in_progress=message.in_progress,
        )
    except Exception as exc:
        logger.error("Workflow trigger execution raised", detail=str(exc))
        await message.nak()
        return {
            "status": "failed",
            "error_kind": DispatchErrorKind.TRANSIENT.value,
            "detail": str(exc),
        }

    status = str(result.get("status", "failed"))
    error_kind = str(result.get("error_kind", ""))
    if status in {"completed", "human_review", "ignored"}:
        await message.ack()
        return result
    if error_kind in _TERMINAL_ERROR_KINDS:
        await message.term()
        return result
    await message.nak()
    return result


async def _fetch_messages(subscription, config: NatsWorkerConfig):
    try:
        return await subscription.fetch(
            batch=config.fetch_batch_size,
            timeout=config.fetch_timeout_seconds,
            heartbeat=config.fetch_heartbeat_seconds,
        )
    except FetchTimeoutError, TimeoutError:
        return []


async def run_nats_worker(
    config: NatsWorkerConfig | None = None,
    *,
    runner: WorkflowTriggerRunner = process_workflow_trigger,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Run the JetStream worker loop until cancelled or stopped."""

    worker_config = config or NatsWorkerConfig()
    bootstrap_app()
    validate_compile_llm_readiness()

    nc = await nats.connect(
        servers=worker_config.servers,
        name=worker_config.client_name,
        connect_timeout=worker_config.connect_timeout_seconds,
    )

    try:
        js = nc.jetstream(timeout=worker_config.js_api_timeout_seconds)
        await _ensure_stream(nc, worker_config)
        subscriptions = [
            await js.pull_subscribe(
                worker_config.draft_subject,
                durable=worker_config.draft_consumer_name,
                stream=worker_config.stream_name,
                config=_consumer_config(worker_config, worker_config.draft_subject),
            ),
            await js.pull_subscribe(
                worker_config.cron_subject,
                durable=worker_config.cron_consumer_name,
                stream=worker_config.stream_name,
                config=_consumer_config(worker_config, worker_config.cron_subject),
            ),
        ]

        logger.info(
            "Starting NATS worker",
            stream_name=worker_config.stream_name,
            draft_subject=worker_config.draft_subject,
            cron_subject=worker_config.cron_subject,
        )

        while True:
            if stop_event is not None and stop_event.is_set():
                break

            processed_any = False
            for subscription in subscriptions:
                messages = await _fetch_messages(subscription, worker_config)
                if not messages:
                    continue
                processed_any = True
                for message in messages:
                    await process_jetstream_message(
                        message,
                        runner=runner,
                        heartbeat_interval=worker_config.in_progress_heartbeat_seconds,
                    )

            if not processed_any and worker_config.idle_sleep_seconds > 0:
                await asyncio.sleep(worker_config.idle_sleep_seconds)
    finally:
        try:
            await nc.drain()
        except ConnectionClosedError, NoServersError, TimeoutError:
            await nc.close()
