from abc import ABC

from typing import Awaitable, Callable, List, Optional
from datetime import datetime
from waygate_core.schemas import RawDocument


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

    async def listen(
        self, on_data_callback: Callable[[List[RawDocument]], Awaitable[None]]
    ):
        """Start a persistent listener and push data to `on_data_callback`.

        Implementations should `await on_data_callback(docs)` whenever new
        `RawDocument` objects are available from the live stream.
        """

        raise NotImplementedError()
