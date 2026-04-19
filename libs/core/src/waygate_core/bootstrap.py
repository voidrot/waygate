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
    storage: dict[str, StoragePlugin]
    webhooks: dict[str, WebhookPlugin]
    llm: dict[str, LLMProviderPlugin]
    cron: dict[str, CronPlugin]
    communication: dict[str, CommunicationClientPlugin]


@dataclass(frozen=True)
class WaygateAppContext:
    config: WaygateRootSettings
    plugins: WaygatePluginsContext


_app_context: WaygateAppContext | None = None


def bootstrap_app() -> WaygateAppContext:
    """Initialize the Waygate application.

    Three phases:
    1. Configure logging.
    2. Load all plugins via entry points, then discover their config schemas.
    3. Build the merged settings object and instantiate plugins with their configs.
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
    global _app_context
    if _app_context is None:
        _app_context = bootstrap_app()
    return _app_context
