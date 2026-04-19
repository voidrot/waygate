from __future__ import annotations

import os
import re

from pydantic import BaseModel, Field
from redis import Redis
from redis.exceptions import RedisError
from rq import Queue, Retry
from rq.exceptions import DuplicateJobError
from waygate_core.plugin import (
    CommunicationClientPlugin,
    DispatchErrorKind,
    PluginConfigRegistration,
    WorkflowDispatchResult,
    WorkflowTriggerMessage,
)
from waygate_core.plugin.hooks import hookimpl

PLUGIN_NAME = "communication-rq"
_DEFAULT_REDIS_URL = "redis://localhost:6379/0"
_RQ_JOB_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")


class CommunicationRQConfig(BaseModel):
    redis_url: str | None = Field(default=None)
    draft_queue_name: str = Field(default="draft")
    cron_queue_name: str = Field(default="cron")
    job_function: str = Field(
        default="waygate_workflows.draft.jobs.process_workflow_trigger"
    )
    job_timeout: int | str = Field(default="5m")
    result_ttl: int = Field(default=500)
    failure_ttl: int = Field(default=31_536_000)
    retry_max: int = Field(default=3, ge=0)
    retry_intervals: list[int] = Field(default_factory=lambda: [10, 30, 60])
    unique_jobs: bool = Field(default=True)


class CommunicationRQPlugin(CommunicationClientPlugin):
    plugin_name = PLUGIN_NAME

    def __init__(self, config: CommunicationRQConfig | None = None) -> None:
        self._config = config or CommunicationRQConfig()

    @property
    def name(self) -> str:
        return PLUGIN_NAME

    @staticmethod
    @hookimpl
    def waygate_communication_client_plugin() -> type["CommunicationRQPlugin"]:
        return CommunicationRQPlugin

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        return PluginConfigRegistration(name=PLUGIN_NAME, config=CommunicationRQConfig)

    async def submit_workflow_trigger(
        self,
        message: WorkflowTriggerMessage,
    ) -> WorkflowDispatchResult:
        if message.event_type == "draft.ready" and not message.document_paths:
            return WorkflowDispatchResult(
                accepted=False,
                detail="draft.ready triggers require at least one document path",
                error_kind=DispatchErrorKind.VALIDATION,
            )

        queue_name = self._resolve_queue_name(message.event_type)
        if queue_name is None:
            return WorkflowDispatchResult(
                accepted=False,
                detail=f"Unsupported workflow event type: {message.event_type}",
                error_kind=DispatchErrorKind.VALIDATION,
            )

        job_id = self._build_job_id(message)

        try:
            connection = Redis.from_url(self._resolve_redis_url())
            queue = Queue(queue_name, connection=connection)
            enqueue_kwargs: dict[str, object] = {
                "job_timeout": self._config.job_timeout,
                "result_ttl": self._config.result_ttl,
                "failure_ttl": self._config.failure_ttl,
            }

            retry = self._build_retry()
            if retry is not None:
                enqueue_kwargs["retry"] = retry
            if job_id is not None:
                enqueue_kwargs["job_id"] = job_id
                enqueue_kwargs["unique"] = self._config.unique_jobs

            job = queue.enqueue(
                self._config.job_function,
                payload=message.model_dump(mode="json"),
                **enqueue_kwargs,
            )
        except DuplicateJobError:
            return WorkflowDispatchResult(
                accepted=True,
                transport_message_id=job_id,
                detail="Workflow trigger job is already queued",
            )
        except RedisError as exc:
            return WorkflowDispatchResult(
                accepted=False,
                detail=f"communication-rq transient failure: {exc}",
                error_kind=DispatchErrorKind.TRANSIENT,
            )
        except Exception as exc:
            return WorkflowDispatchResult(
                accepted=False,
                detail=f"communication-rq submission failed: {exc}",
                error_kind=DispatchErrorKind.PERMANENT,
            )

        return WorkflowDispatchResult(
            accepted=True,
            transport_message_id=job.id,
            detail="Submitted workflow trigger message to RQ",
        )

    def _resolve_queue_name(self, event_type: str) -> str | None:
        if event_type == "draft.ready":
            return self._config.draft_queue_name
        if event_type == "cron.tick":
            return self._config.cron_queue_name
        return None

    def _resolve_redis_url(self) -> str:
        if self._config.redis_url:
            return self._config.redis_url

        for env_name in (
            "WAYGATE_COMMUNICATION_RQ__REDIS_URL",
            "WAYGATE_CORE__REDIS_DSN",
            "WAYGATE_CORE__REDIS_URL",
        ):
            value = os.getenv(env_name)
            if value:
                return value

        return _DEFAULT_REDIS_URL

    def _build_retry(self) -> Retry | None:
        if self._config.retry_max <= 0:
            return None

        intervals = self._config.retry_intervals or None
        return Retry(max=self._config.retry_max, interval=intervals)

    def _build_job_id(self, message: WorkflowTriggerMessage) -> str | None:
        if not message.idempotency_key:
            return None

        sanitized = _RQ_JOB_ID_PATTERN.sub("-", message.idempotency_key).strip("-")
        if not sanitized:
            return None
        return f"{message.event_type}-{sanitized}"
