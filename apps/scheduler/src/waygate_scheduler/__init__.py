__VERSION__ = "0.1.0"  # x-release-please-version

import asyncio
import signal
from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # ty: ignore[unresolved-import]
from apscheduler.triggers.cron import CronTrigger  # ty: ignore[unresolved-import]
from waygate_core import bootstrap_app
from waygate_core.logging import get_logger
from waygate_core.plugin import (
    CommunicationClientPlugin,
    WorkflowTriggerMessage,
    resolve_communication_client,
)

logger = get_logger(__name__)


def _resolve_communication_client(app_context) -> CommunicationClientPlugin:
    return resolve_communication_client(
        app_context.plugins.communication,
        app_context.config.core.communication_plugin_name,
        allow_fallback=False,
    )


async def _run_cron_plugin(
    cron_plugin,
    client: CommunicationClientPlugin,
) -> None:
    try:
        await cron_plugin.run({"source": "waygate-scheduler", "mode": "scheduled"})
        dispatch_result = await client.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="cron.tick",
                source=f"waygate-scheduler.cron.{cron_plugin.name}",
                metadata={"schedule": cron_plugin.schedule},
            )
        )
        if dispatch_result.accepted:
            logger.info(f"Dispatched cron trigger for plugin '{cron_plugin.name}'")
        else:
            logger.warning(
                f"Failed to dispatch cron trigger for plugin '{cron_plugin.name}': {dispatch_result.detail}"
            )
    except Exception as exc:
        logger.error(f"Cron plugin '{cron_plugin.name}' execution failed: {exc}")


def _build_cron_job(
    cron_plugin,
    client: CommunicationClientPlugin,
) -> Callable[[], Awaitable[None]]:
    async def _job() -> None:
        await _run_cron_plugin(cron_plugin, client)

    return _job


def _register_cron_jobs(
    scheduler: AsyncIOScheduler,
    app_context,
    client: CommunicationClientPlugin,
) -> None:
    for plugin_key, cron_plugin in app_context.plugins.cron.items():
        scheduler.add_job(
            _build_cron_job(cron_plugin, client),
            trigger=CronTrigger.from_crontab(cron_plugin.schedule),
            id=f"cron:{plugin_key}",
            name=f"cron:{cron_plugin.name}",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        logger.info(
            "Registered cron job "
            f"id='cron:{plugin_key}' plugin='{cron_plugin.name}' schedule='{cron_plugin.schedule}'"
        )


def _install_signal_handlers(loop, stop_event: asyncio.Event) -> None:
    def _request_shutdown(sig_name: str) -> None:
        logger.info(f"Received {sig_name}; shutting down scheduler")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown, sig.name)
        except NotImplementedError:
            logger.warning(
                f"Signal handlers are not supported in this runtime (signal={sig.name})"
            )


async def _run_scheduler() -> None:
    app_context = bootstrap_app()

    cron_plugin_count = len(app_context.plugins.cron)
    logger.info(f"Loaded {cron_plugin_count} cron plugin(s)")
    if cron_plugin_count == 0:
        return

    client = _resolve_communication_client(app_context)

    scheduler = AsyncIOScheduler()
    _register_cron_jobs(scheduler, app_context, client)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    _install_signal_handlers(loop, stop_event)

    scheduler.start()
    logger.info("Scheduler started")

    try:
        await stop_event.wait()
    finally:
        logger.info("Scheduler stopping")
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def main() -> None:
    asyncio.run(_run_scheduler())
