"""Plugin registry for the receiver service.

The registry discovers ingestion plugins via the
`waygate.apps.receiver.plugins` entry point group and keeps instantiated
plugin objects keyed by their `plugin_name` for lookup by the rest of
the application.
"""

import importlib
import logging
from typing import Dict, Optional
import importlib.metadata

from waygate_core.plugin_base import IngestionPlugin

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Container for discovered `IngestionPlugin` instances.

    Use `discover_and_register()` to populate the registry from entry
    points. Callers can retrieve a single plugin with `get(name)` or a
    mapping of all registered plugins with `get_all()`.
    """

    def __init__(self) -> None:
        self._plugins: Dict[str, IngestionPlugin] = {}

    def discover_and_register(self) -> None:
        """Discover and instantiate plugins exposed via entry points.

        This method iterates over entry points in the
        `waygate.apps.receiver.plugins` group, attempts to load and
        instantiate each plugin class, and registers instances that
        subclass `IngestionPlugin`.

        Any import/initialization errors are logged and skipped so a
        broken plugin does not stop discovery of other plugins.
        """

        entry_points = importlib.metadata.entry_points(group="waygate.plugins.receiver")
        for ep in entry_points:
            try:
                plugin_class = ep.load()
                plugin_instance = plugin_class()

                if isinstance(plugin_instance, IngestionPlugin):
                    self._plugins[plugin_instance.plugin_name] = plugin_instance
                    logger.info("Registered plugin: %s", plugin_instance.plugin_name)
                else:
                    logger.warning(
                        "Plugin %s does not inherit from IngestionPlugin and will be skipped.",
                        ep.name,
                    )
            except Exception:
                logger.exception(
                    "Error loading plugin %s", getattr(ep, "name", str(ep))
                )

    def get(self, name: str) -> Optional[IngestionPlugin]:
        """Return the plugin instance registered under `name`.

        Returns `None` if no plugin with that name exists.
        """

        return self._plugins.get(name)

    def get_all(self) -> Dict[str, IngestionPlugin]:
        """Return a mapping of plugin name -> plugin instance for all registered plugins.

        A shallow copy is returned to prevent external mutation of the
        registry's internal state.
        """

        return dict(self._plugins)


registry = PluginRegistry()
