from abc import ABC


class WayGatePluginBase(ABC):
    """
    Base class for WayGate plugins.

    **Plugin Lifecycle & Caching:**

    Plugin instances are discovered and instantiated once during application startup,
    then cached process-wide in the WayGatePluginManager. Instances are shared across
    all consumers (API, Conductor, Scheduler) for the lifetime of the process.

    **Thread Safety:**

    Implement plugins as stateless where possible. If your plugin maintains mutable
    instance state, ensure it is thread-safe, as multiple application components may
    call your plugin methods concurrently.
    """

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
