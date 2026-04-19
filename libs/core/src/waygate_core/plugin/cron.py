from abc import ABC, abstractmethod


class CronPlugin(ABC):
    """
    Base class for cron plugins.

    Cron plugin instances are cached process-wide and invoked on a schedule.
    Implement your plugin as idempotent and stateless where possible.
    """

    plugin_group: str = "waygate.plugins.cron"
    hook_name: str = "waygate_cron_plugin"

    @property
    def name(self) -> str:
        """
        The name of the plugin.

        Returns:
            str: The name of the plugin.
        """
        return self.__class__.__name__

    @property
    def description(self) -> str:
        """
        A brief description of the plugin.

        Returns:
            str: A description of the plugin.
        """
        return "No description provided."

    @property
    def version(self) -> str:
        """
        The version of the plugin.

        Returns:
            str: The version of the plugin.
        """
        return "0.0.0"

    @property
    def schedule(self) -> str:
        """
        The cron schedule for this plugin.

        Returns:
            str: A cron schedule string (e.g. "0 * * * *" for hourly).
        """
        raise NotImplementedError(
            "CronPlugin subclasses must define a schedule property"
        )

    @abstractmethod
    async def run(self, payload: dict):
        """
        Handle an incoming cron event.

        Args:
            payload (dict): The event payload to process.
        """
        raise NotImplementedError("CronPlugin subclasses must implement run")
