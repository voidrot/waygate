"""Application bootstrap and frozen runtime context objects for WayGate.

The bootstrap path configures logging, loads plugins, builds merged settings,
and memoizes the resulting process-wide application context.
"""

from dataclasses import dataclass
from typing import cast

from waygate_core.config.registry import WaygateRootSettings
from waygate_core.plugin.communication import CommunicationClientPlugin
from waygate_core.logging import configure_logging
from waygate_core.plugin.cron import CronPlugin
from waygate_core.plugin.llm import LLMProviderPlugin
from waygate_core.plugin.storage import StoragePlugin
from waygate_core.plugin.webhook import WebhookPlugin


@dataclass(frozen=True)
class WaygatePluginsContext:
    """Concrete plugin instances grouped by runtime category."""

    storage: dict[str, StoragePlugin]
    webhooks: dict[str, WebhookPlugin]
    llm: dict[str, LLMProviderPlugin]
    cron: dict[str, CronPlugin]
    communication: dict[str, CommunicationClientPlugin]


@dataclass(frozen=True)
class WaygateAppContext:
    """Resolved configuration and instantiated plugins for the current process."""

    config: WaygateRootSettings
    plugins: WaygatePluginsContext


_app_context: WaygateAppContext | None = None


def bootstrap_app() -> WaygateAppContext:
    """Initialize the WayGate application.

    The bootstrap process configures logging, loads plugins, builds merged
    settings, and instantiates the grouped plugin runtime.

    Returns:
        The frozen application context for the current process.
    """
    from waygate_core.config.registry import ConfigRegistry
    from waygate_core.plugin.registry import shared_plugin_manager

    configure_logging()
    shared_plugin_manager.load_all()
    config = ConfigRegistry(shared_plugin_manager).build_config()

    return WaygateAppContext(
        config=config,
        plugins=WaygatePluginsContext(
            storage=cast(
                dict[str, StoragePlugin],
                shared_plugin_manager.get_plugins("waygate.plugins.storage", config),
            ),
            webhooks=cast(
                dict[str, WebhookPlugin],
                shared_plugin_manager.get_plugins("waygate.plugins.webhooks", config),
            ),
            llm=cast(
                dict[str, LLMProviderPlugin],
                shared_plugin_manager.get_plugins("waygate.plugins.llm", config),
            ),
            cron=cast(
                dict[str, CronPlugin],
                shared_plugin_manager.get_plugins("waygate.plugins.cron", config),
            ),
            communication=cast(
                dict[str, CommunicationClientPlugin],
                shared_plugin_manager.get_plugins(
                    "waygate.plugins.communication", config
                ),
            ),
        ),
    )


def get_app_context() -> WaygateAppContext:
    """Return the cached application context.

    If the context has not been initialized yet, this function bootstraps the
    process first and then returns the cached value.

    Returns:
        The process-wide application context.
    """

    global _app_context
    if _app_context is None:
        _app_context = bootstrap_app()
    return _app_context
