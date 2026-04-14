from abc import abstractmethod
from waygate_core.plugin.base import WayGatePluginBase


class CronPlugin(WayGatePluginBase):
    """
    Base class for cron plugins.

    Cron plugin instances are cached process-wide and invoked on a schedule.
    Implement your plugin as idempotent and stateless where possible.
    """

    plugin_group: str = "waygate.plugins.cron"
    hook_name: str = "waygate_cron_plugin"

    @property
    def schedule(self) -> str:
        """
        The cron schedule for this plugin.

        Returns:
            str: A cron schedule string (e.g. "0 * * * *" for hourly).
        """
        return "* * * * *"  # Default to running every minute

    @abstractmethod
    async def run(self, payload: dict):
        """
        Handle an incoming cron event.

        Args:
            payload (dict): The event payload to process.
        """
        raise NotImplementedError("CronPlugin subclasses must implement run")
