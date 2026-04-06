# libs/core/llm.py
from typing import TypeVar, Type, Optional
from pydantic import BaseModel
from langchain_core.runnables import Runnable
from waygate_core.llm_registry import llm_registry

T = TypeVar("T", bound=BaseModel)

# Discover plugins once when the module loads
llm_registry.discover_providers()


def get_structured_llm(
    provider_name: str,
    schema: Type[T],
    model_name: Optional[str] = None,
    temperature: float = 0.0,
) -> Runnable:
    """
    Factory function used by all LangGraph nodes to get an LLM.
    The actual implementation is delegated to the active plugin.
    """
    provider = llm_registry.get_provider(provider_name)
    return provider.get_structured_llm(schema, model_name, temperature)


def get_llm(
    provider_name: str,
    model_name: Optional[str] = None,
    temperature: float = 0.0,
) -> Runnable:
    """
    Factory function used by all LangGraph nodes to get an LLM.
    The actual implementation is delegated to the active plugin.
    """
    provider = llm_registry.get_provider(provider_name)
    return provider.get_llm(model_name, temperature)
