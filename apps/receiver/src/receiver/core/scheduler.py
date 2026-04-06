import logging

from receiver.core.registry import registry
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from receiver.services.trigger import save_and_trigger_langgraph_async

scheduler = AsyncIOScheduler()

logger = logging.getLogger(__name__)


async def poll_plugin_job(plugin_name: str):
    plugin = registry.get(plugin_name)
    if not plugin:
        logger.error("Plugin '%s' not found for polling job", plugin_name)
        return

    try:
        last_polled = None  # TODO: track last polled timestamp per plugin
        raw_documents = plugin.poll(since_timestamp=last_polled)

        if raw_documents:
            await save_and_trigger_langgraph_async(raw_documents)
            logger.info(
                "Polled %d new documents from plugin '%s'",
                len(raw_documents),
                plugin_name,
            )
    except NotImplementedError:
        logger.warning("Plugin '%s' does not implement polling", plugin_name)
    except Exception as e:
        logger.exception(
            "Error during polling job for plugin '%s': %s", plugin_name, str(e)
        )


def setup_scheduler():
    for plugin_name, plugin in registry.get_all().items():
        if hasattr(plugin, "cron_schedule") and plugin.cron_schedule:
            scheduler.add_job(
                poll_plugin_job,
                "cron",
                **plugin.cron_schedule,
                args=[plugin_name],
                id=f"poll_{plugin_name}",
                replace_existing=True,
            )
