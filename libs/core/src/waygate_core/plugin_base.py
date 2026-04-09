from abc import ABC

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional
from datetime import datetime
from waygate_core.schemas import RawDocument

if TYPE_CHECKING:
    from .settings_registry import SettingDefinition


class WebhookVerificationError(ValueError):
    """Raised when a webhook request fails authenticity or freshness checks."""


class IngestionPlugin(ABC):
    """Abstract base class for ingestion plugins.

    Implementations should provide one or more of the following integration
    points depending on how the source delivers data:

    - `poll()`: periodically called to fetch new documents.
    - `handle_webhook()`: invoked when an incoming HTTP webhook is received.
    - `listen()`: an async long-running listener (e.g., WebSocket) that
      pushes incoming documents to the provided callback.

    The receiver expects these methods to return a list of `RawDocument`
    instances representing newly ingested items.

    Implementations should populate canonical metadata whenever possible,
    including `source_url`, `source_hash`, `visibility`, and typed
    `source_metadata` for known source types.
    """

    @property
    def plugin_name(self) -> str:
        """Human-readable plugin name used for logging and registry keys.

        Override this property in subclasses when a different name is desired.
        """

        return "base_plugin"

    @property
    def cron_schedule(self) -> Optional[dict]:
        """Optional cron schedule for polling.

        If defined, the receiver will set up a scheduled job to call `poll()`
        according to this schedule. The dictionary should contain valid cron
        trigger arguments (e.g., `{"hour": "*/1"}` for hourly).
        """

        return {}

    @property
    def settings_definitions(self) -> list["SettingDefinition"]:
        return []

    def get_settings_values(self) -> dict[str, Any]:
        from waygate_core.settings import get_runtime_settings
        from waygate_core.settings_registry import resolve_settings_values
        from waygate_core.settings_store import (
            PostgresSettingsStore,
            build_plugin_settings_namespace,
        )

        definitions = list(self.settings_definitions)
        if not definitions:
            return {}

        runtime_settings = get_runtime_settings()
        stored_values: dict[str, Any] = {}
        if runtime_settings.runtime_settings_backend == "postgres":
            if not runtime_settings.postgres_dsn:
                raise ValueError(
                    "POSTGRES_DSN must be set when RUNTIME_SETTINGS_BACKEND=postgres"
                )
            store = PostgresSettingsStore(runtime_settings.postgres_dsn)
            stored_values = store.get_namespace(
                build_plugin_settings_namespace(self.plugin_name)
            )

        resolved = resolve_settings_values(
            definitions,
            stored_values,
            runtime_backend=runtime_settings.runtime_settings_backend,
        )
        return {key: value.value for key, value in resolved.items()}

    def poll(self, since_timestamp: Optional[datetime] = None) -> List[RawDocument]:
        """Poll the source for new documents.

        Args:
            since_timestamp: optional datetime to fetch only newer items.

        Returns:
            A list of `RawDocument` instances discovered since `since_timestamp`.
        """

        raise NotImplementedError()

    def handle_webhook(self, payload: dict) -> List[RawDocument]:
        """Handle an incoming webhook payload and return discovered documents.

        Args:
            payload: the JSON-decoded webhook body.

        Returns:
            A list of `RawDocument` instances parsed from the payload.
        """

        raise NotImplementedError()

    def verify_webhook_request(
        self,
        headers: Mapping[str, str],
        body: bytes,
    ) -> None:
        """Verify webhook authenticity before payload decoding.

        Implementations should raise `WebhookVerificationError` when a
        request must be rejected.
        """

        return None

    def prepare_webhook_payload(
        self,
        payload: Any,
        headers: Mapping[str, str],
    ) -> Any:
        """Optionally enrich a decoded webhook payload using request headers."""

        return payload

    async def listen(
        self, on_data_callback: Callable[[List[RawDocument]], Awaitable[None]]
    ):
        """Start a persistent listener and push data to `on_data_callback`.

        Implementations should `await on_data_callback(docs)` whenever new
        `RawDocument` objects are available from the live stream.
        """

        raise NotImplementedError()
