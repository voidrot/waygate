from __future__ import annotations

from dataclasses import dataclass

from waygate_core.config import ConfigRegistry
from waygate_core.config.registry import WaygateRootSettings
from waygate_core.logging import configure_logging, get_logger
from waygate_core.plugin import (
    BaseLLMProvider,
    CronPlugin,
    PluginGroups,
    StoragePlugin,
    WebhookPlugin,
    shared_plugin_manager,
)


logger = get_logger()


@dataclass(frozen=True)
class WaygatePluginsContext:
    storage: dict[str, StoragePlugin]
    webhooks: dict[str, WebhookPlugin]
    llm: dict[str, BaseLLMProvider]
    cron: dict[str, CronPlugin]


@dataclass(frozen=True)
class WaygateAppContext:
    config: WaygateRootSettings
    plugins: WaygatePluginsContext


_app_context: WaygateAppContext | None = None


def init_app() -> WaygateAppContext:
    global _app_context

    if _app_context is not None:
        return _app_context

    configure_logging()
    logger.debug("Configured Logging...")
    logger.info("Initializing Waygate application...")

    # 1. Build config — discovers plugin schemas and populates settings from env vars.
    logger.debug("Discovering plugins and configuration...")
    config = ConfigRegistry(plugin_manager=shared_plugin_manager).build_config()

    # 2. Instantiate all plugin groups once, injecting each plugin's config in the
    #    same pass. After this call get_plugins() is just a cache read.
    shared_plugin_manager.configure_from_settings(config)

    storage_plugins = shared_plugin_manager.get_plugins(PluginGroups.STORAGE)
    webhook_plugins = shared_plugin_manager.get_plugins(PluginGroups.WEBHOOKS)
    llm_plugins = shared_plugin_manager.get_plugins(PluginGroups.LLM)
    cron_plugins = shared_plugin_manager.get_plugins(PluginGroups.CRON)

    _app_context = WaygateAppContext(
        config=config,
        plugins=WaygatePluginsContext(
            storage=storage_plugins,
            webhooks=webhook_plugins,
            llm=llm_plugins,
            cron=cron_plugins,
        ),
    )

    logger.info("Waygate application initialized successfully.")
    return _app_context


def get_app_context() -> WaygateAppContext:
    if _app_context is None:
        return init_app()
    return _app_context
