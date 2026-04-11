from pydantic_settings import BaseSettings
from abc import ABC


class WayGatePluginBase(ABC):
    """
    Base class for WayGate plugins.
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

    @property
    def config(self) -> BaseSettings | None:
        """
        The configuration for the plugin.

        Returns:
            BaseSettings: The plugin's configuration.
        """
        return None
