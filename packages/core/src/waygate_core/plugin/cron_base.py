from waygate_core.plugin.base import WayGatePluginBase


class CronPlugin(WayGatePluginBase):
    """
    Base class for cron plugins.
    """

    @property
    def schedule(self) -> str:
        """
        The cron schedule for this plugin.

        Returns:
            str: A cron schedule string (e.g. "0 * * * *" for hourly).
        """
        return "* * * * *"  # Default to running every minute

    async def run(self, payload: dict):
        """
        Handle an incoming cron event.

        Args:
            payload (dict): The event payload to process.
        """
        raise NotImplementedError("CronPlugin subclasses must implement run")
