from pydantic import BaseModel
from typing import Type, TypeVar
from langchain_core.runnables import Runnable
from abc import abstractmethod
from waygate_core.plugin.base import WayGatePluginBase

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(WayGatePluginBase):
    """
    Abstract base for LLM provider plugins.

    LLM provider instances are cached process-wide at startup. Implement your
    provider as stateless where possible, or ensure thread-safe access to any
    mutable state.
    """

    plugin_group: str = "waygate.plugins.llm"
    hook_name: str = "waygate_llm_plugin"

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
