from pydantic import BaseModel
from typing import Type, TypeVar
from abc import ABC, abstractmethod
from langchain_core.runnables import Runnable

T = TypeVar("T", bound=BaseModel)


class LLMProviderPlugin(ABC):
    """
    Abstract base for LLM provider plugins.

    LLM provider instances are cached process-wide at startup. Implement your
    provider as stateless where possible, or ensure thread-safe access to any
    mutable state.
    """

    plugin_group: str = "waygate.plugins.llm"
    hook_name: str = "waygate_llm_provider_plugin"

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

    @abstractmethod
    def get_llm(self, model_name: str, workflow_type: str | None = None) -> Runnable:
        """
        Retrieve an LLM instance by name.

        Args:
            model_name (str): The name of the LLM model to retrieve.

        Returns:
            An instance of the requested LLM model.
        """
        raise NotImplementedError("BaseLLMProvider subclasses must implement get_llm")

    @abstractmethod
    def get_structured_llm(
        self, schema: Type[T], model_name: str, workflow_type: str | None = None
    ) -> Runnable:
        """
        Retrieve a structured LLM instance that outputs data conforming to the provided schema.

        Args:
            schema (Type[T]): A Pydantic model class that defines the expected output structure.
            model_name (str | None): The name of the LLM model to retrieve. If None, a default model will be used.

        Returns:
            StructuredLLM[T]: An instance of StructuredLLM that will output data conforming to the provided schema.
        """
        raise NotImplementedError(
            "BaseLLMProvider subclasses must implement get_structured_llm"
        )
