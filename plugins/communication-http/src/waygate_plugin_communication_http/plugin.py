"""HTTP transport for WayGate workflow trigger messages."""

from __future__ import annotations

import asyncio
import httpx
from pydantic import BaseModel, Field
from waygate_core.plugin import (
    CommunicationClientPlugin,
    CommunicationWorkerTransportPlugin,
    DispatchErrorKind,
    PluginConfigRegistration,
    WorkflowTriggerRunner,
    WorkflowDispatchResult,
    WorkflowTriggerMessage,
)
from waygate_core.plugin.hooks import hookimpl
from waygate_worker import HTTPWorkerConfig, run_http_worker

PLUGIN_NAME = "communication-http"


class CommunicationHttpConfig(BaseModel):
    """Configuration for the HTTP communication transport."""

    endpoint: str = Field(default="http://localhost:8090/workflows/trigger")
    timeout_seconds: float = Field(default=5.0)
    max_retries: int = Field(default=2, ge=0)
    retry_backoff_seconds: float = Field(default=0.25, gt=0)
    auth_token: str | None = Field(default=None)
    auth_header: str = Field(default="Authorization")
    worker_host: str = Field(default="0.0.0.0")
    worker_port: int = Field(default=8090, ge=1, le=65535)
    worker_endpoint_path: str = Field(default="/workflows/trigger")


class CommunicationHttpPlugin(CommunicationClientPlugin):
    """Submit workflow triggers to a worker endpoint over HTTP."""

    plugin_name = PLUGIN_NAME

    def __init__(self, config: CommunicationHttpConfig | None = None) -> None:
        """Initialize the HTTP transport plugin.

        Args:
            config: Optional plugin configuration.
        """

        self._config = config or CommunicationHttpConfig()

    @property
    def name(self) -> str:
        """Return the canonical plugin name.

        Returns:
            The plugin name used for registration and lookups.
        """

        return PLUGIN_NAME

    @staticmethod
    @hookimpl
    def waygate_communication_client_plugin() -> type["CommunicationHttpPlugin"]:
        """Register the HTTP communication client implementation.

        Returns:
            The plugin class to register with Pluggy.
        """

        return CommunicationHttpPlugin

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        """Register the plugin configuration model.

        Returns:
            The plugin config registration metadata.
        """

        return PluginConfigRegistration(
            name=PLUGIN_NAME,
            config=CommunicationHttpConfig,
        )

    @staticmethod
    @hookimpl
    def waygate_worker_transport_plugin() -> type["CommunicationHttpWorkerTransport"]:
        """Register the HTTP worker transport companion."""

        return CommunicationHttpWorkerTransport

    async def submit_workflow_trigger(
        self,
        message: WorkflowTriggerMessage,
    ) -> WorkflowDispatchResult:
        """Submit a workflow trigger message over HTTP.

        Args:
            message: The trigger message to submit.

        Returns:
            The dispatch result describing the transport outcome.
        """

        if not self._config.endpoint.strip():
            return WorkflowDispatchResult(
                accepted=False,
                detail="communication-http endpoint is not configured",
                error_kind=DispatchErrorKind.CONFIG,
            )

        if message.event_type == "draft.ready" and not message.document_paths:
            return WorkflowDispatchResult(
                accepted=False,
                detail="draft.ready triggers require at least one document path",
                error_kind=DispatchErrorKind.VALIDATION,
            )

        headers: dict[str, str] = {"content-type": "application/json"}
        if self._config.auth_token:
            headers[self._config.auth_header] = self._config.auth_token

        attempts = self._config.max_retries + 1
        for attempt in range(attempts):
            try:
                # Create a short-lived client per attempt so retries stay bounded.
                async with httpx.AsyncClient(
                    timeout=self._config.timeout_seconds
                ) as client:
                    response = await client.post(
                        self._config.endpoint,
                        headers=headers,
                        json=message.model_dump(mode="json"),
                    )
                    response.raise_for_status()
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                if attempt < self._config.max_retries:
                    await asyncio.sleep(
                        self._config.retry_backoff_seconds * (2**attempt)
                    )
                    continue

                return WorkflowDispatchResult(
                    accepted=False,
                    detail=f"communication-http transient failure: {exc}",
                    error_kind=DispatchErrorKind.TRANSIENT,
                )
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                is_transient = status_code >= 500 or status_code in {408, 425, 429}
                if is_transient and attempt < self._config.max_retries:
                    await asyncio.sleep(
                        self._config.retry_backoff_seconds * (2**attempt)
                    )
                    continue

                return WorkflowDispatchResult(
                    accepted=False,
                    detail=f"communication-http submission failed with status {status_code}",
                    error_kind=(
                        DispatchErrorKind.TRANSIENT
                        if is_transient
                        else DispatchErrorKind.PERMANENT
                    ),
                )
            except httpx.HTTPError as exc:
                return WorkflowDispatchResult(
                    accepted=False,
                    detail=f"communication-http submission failed: {exc}",
                    error_kind=DispatchErrorKind.PERMANENT,
                )
            break

        payload = response.json() if response.content else {}
        message_id = payload.get("message_id") if isinstance(payload, dict) else None

        # The worker response only needs to expose an identifier for tracing.

        return WorkflowDispatchResult(
            accepted=True,
            transport_message_id=message_id,
            detail="Submitted workflow trigger message",
            error_kind=None,
        )


class CommunicationHttpWorkerTransport(CommunicationWorkerTransportPlugin):
    """Serve workflow trigger requests over HTTP."""

    plugin_name = PLUGIN_NAME

    def __init__(self, config: CommunicationHttpConfig | None = None) -> None:
        self._config = config or CommunicationHttpConfig()

    @property
    def name(self) -> str:
        return PLUGIN_NAME

    async def run(
        self,
        runner: WorkflowTriggerRunner,
        *,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        config = HTTPWorkerConfig(
            host=self._config.worker_host,
            port=self._config.worker_port,
            endpoint_path=self._config.worker_endpoint_path,
            auth_token=self._config.auth_token,
            auth_header=self._config.auth_header,
        )
        await run_http_worker(config, runner=runner, stop_event=stop_event)
