"""JetStream transport for WayGate workflow trigger messages."""

from __future__ import annotations

import json
import re
from typing import Annotated

import nats
from nats.errors import ConnectionClosedError, NoServersError, TimeoutError
from nats.js.api import StorageType, StreamConfig
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import NoDecode

from waygate_core.plugin import (
    CommunicationClientPlugin,
    DispatchErrorKind,
    PluginConfigRegistration,
    WorkflowDispatchResult,
    WorkflowTriggerMessage,
)
from waygate_core.plugin.hooks import hookimpl

PLUGIN_NAME = "communication-nats"
_NATS_MESSAGE_ID_PATTERN = re.compile(r"[^a-zA-Z0-9._:-]+")


class CommunicationNatsConfig(BaseModel):
    """Configuration for the NATS communication transport."""

    servers: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["nats://localhost:4222"]
    )
    stream_name: str = Field(default="WAYGATE_WORKFLOW")
    draft_subject: str = Field(default="waygate.workflow.draft")
    cron_subject: str = Field(default="waygate.workflow.cron")
    client_name: str = Field(default="waygate-communication-nats")
    connect_timeout_seconds: float = Field(default=2.0, gt=0)
    publish_timeout_seconds: float = Field(default=5.0, gt=0)

    @field_validator("servers", mode="before")
    @classmethod
    def _normalize_servers(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("servers must be a list[str] or comma-delimited string")


class CommunicationNatsPlugin(CommunicationClientPlugin):
    """Publish workflow trigger messages to JetStream subjects."""

    plugin_name = PLUGIN_NAME

    def __init__(self, config: CommunicationNatsConfig | None = None) -> None:
        self._config = config or CommunicationNatsConfig()

    @property
    def name(self) -> str:
        return PLUGIN_NAME

    @staticmethod
    @hookimpl
    def waygate_communication_client_plugin() -> type["CommunicationNatsPlugin"]:
        return CommunicationNatsPlugin

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        return PluginConfigRegistration(
            name=PLUGIN_NAME, config=CommunicationNatsConfig
        )

    async def submit_workflow_trigger(
        self,
        message: WorkflowTriggerMessage,
    ) -> WorkflowDispatchResult:
        if (
            message.event_type in {"draft.ready", "ready.integrate"}
            and not message.document_paths
        ):
            return WorkflowDispatchResult(
                accepted=False,
                detail=(
                    f"{message.event_type} triggers require at least one document path"
                ),
                error_kind=DispatchErrorKind.VALIDATION,
            )

        subject = self._resolve_subject(message.event_type)
        if subject is None:
            return WorkflowDispatchResult(
                accepted=False,
                detail=f"Unsupported workflow event type: {message.event_type}",
                error_kind=DispatchErrorKind.VALIDATION,
            )

        message_id = self._build_message_id(message)
        headers = {"Nats-Msg-Id": message_id} if message_id is not None else None
        connection = None
        try:
            connection = await nats.connect(
                servers=self._config.servers,
                name=self._config.client_name,
                connect_timeout=self._config.connect_timeout_seconds,
            )
            jetstream = connection.jetstream(
                timeout=self._config.publish_timeout_seconds
            )
            await self._ensure_stream(connection)
            ack = await jetstream.publish(
                subject,
                json.dumps(message.model_dump(mode="json")).encode("utf-8"),
                stream=self._config.stream_name,
                headers=headers,
                timeout=self._config.publish_timeout_seconds,
            )
        except (NoServersError, ConnectionClosedError, TimeoutError) as exc:
            return WorkflowDispatchResult(
                accepted=False,
                detail=f"communication-nats transient failure: {exc}",
                error_kind=DispatchErrorKind.TRANSIENT,
            )
        except Exception as exc:
            status_code = getattr(exc, "code", None)
            error_kind = self._classify_error_kind(status_code)
            return WorkflowDispatchResult(
                accepted=False,
                detail=f"communication-nats submission failed: {exc}",
                error_kind=error_kind,
            )
        finally:
            if connection is not None:
                try:
                    await connection.drain()
                except Exception:
                    await connection.close()

        transport_message_id = message_id or f"{ack.stream}:{ack.seq}"
        detail = (
            "Workflow trigger message already present in JetStream"
            if getattr(ack, "duplicate", False)
            else "Submitted workflow trigger message to NATS"
        )
        return WorkflowDispatchResult(
            accepted=True,
            transport_message_id=transport_message_id,
            detail=detail,
        )

    def _resolve_subject(self, event_type: str) -> str | None:
        if event_type == "draft.ready":
            return self._config.draft_subject
        if event_type == "ready.integrate":
            return self._config.draft_subject
        if event_type == "cron.tick":
            return self._config.cron_subject
        return None

    async def _ensure_stream(self, connection) -> None:
        jetstream = connection.jetstream(timeout=self._config.publish_timeout_seconds)
        stream_config = StreamConfig(
            name=self._config.stream_name,
            subjects=[self._config.draft_subject, self._config.cron_subject],
            storage=StorageType.FILE,
        )
        try:
            info = await jetstream.stream_info(self._config.stream_name)
        except Exception as exc:
            status_code = getattr(exc, "code", None)
            if status_code != 404:
                raise
            await jetstream.add_stream(config=stream_config)
            return

        existing_subjects = set(info.config.subjects or [])
        desired_subjects = set(stream_config.subjects or [])
        if existing_subjects != desired_subjects:
            await jetstream.update_stream(config=stream_config)

    def _build_message_id(self, message: WorkflowTriggerMessage) -> str | None:
        if not message.idempotency_key:
            return None
        sanitized = _NATS_MESSAGE_ID_PATTERN.sub("-", message.idempotency_key).strip(
            "-"
        )
        if not sanitized:
            return None
        return f"{message.event_type}:{sanitized}"

    def _classify_error_kind(self, status_code: object) -> DispatchErrorKind:
        if status_code in {404, 409}:
            return DispatchErrorKind.CONFIG
        if status_code in {500, 503}:
            return DispatchErrorKind.TRANSIENT
        return DispatchErrorKind.PERMANENT
