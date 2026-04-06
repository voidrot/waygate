from langchain_ollama import ChatOllama
from waygate_core.llm_base import LLMProviderPlugin
import os


class OllamaLLMProvider(LLMProviderPlugin):
    @property
    def provider_name(self) -> str:
        return "ollama"

    def get_llm(self, model_name=None, temperature=0.0):
        target_model = model_name or "llama3.1:8b"
        llm = ChatOllama(
            model=target_model,
            temperature=temperature,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
        return llm

    def get_structured_llm(self, schema, model_name=None, temperature=0.0):
        target_model = model_name or "llama3.1:8b"
        llm = ChatOllama(
            model=target_model,
            temperature=temperature,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
        return llm.with_structured_output(schema)
