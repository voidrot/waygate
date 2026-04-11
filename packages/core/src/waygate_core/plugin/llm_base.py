from pydantic import BaseModel
from typing import Type, TypeVar
from langchain_core.runnables import Runnable
from abc import abstractmethod
from waygate_core.plugin.base import WayGatePluginBase

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(WayGatePluginBase):
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
