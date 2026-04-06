from typing import Optional, Type, TypeVar
from abc import ABC, abstractmethod

from pydantic import BaseModel
from langchain_core.runnables import Runnable

T = TypeVar("T", bound=BaseModel)


class LLMProviderPlugin(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """A unique name for this LLM provider (e.g., 'openai', 'azure', 'anthropic')."""
        pass

    @abstractmethod
    def get_llm(
        self, model_name: Optional[str] = None, temperature: float = 0.0
    ) -> Runnable:
        """Return a LangChain Runnable that wraps the LLM client."""
        pass

    @abstractmethod
    def get_structured_llm(
        self, schema: Type[T], model_name: Optional[str], temperature: float = 0.0
    ) -> Runnable:
        pass
