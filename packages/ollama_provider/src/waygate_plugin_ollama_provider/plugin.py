from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_core.runnables import Runnable
from waygate_core.plugin import BaseLLMProvider, PluginConfigRegistration, hookimpl
from langchain_ollama import ChatOllama
from . import PLUGIN_NAME, __version__


class OllamaProviderConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="waygate_ollama_provider_")

    base_url: str = Field(
        default="http://localhost:11434",
        description="The base URL for the Ollama API.",
    )

    draft_num_ctx: int = Field(
        default=2048,
        description="The context size for the Ollama model when used in draft workflows.",
    )
    draft_top_k: int = Field(
        default=40,
        description="The top_k setting for the Ollama model when used in draft workflows.",
    )
    draft_top_p: float = Field(
        default=0.9,
        description="The top_p setting for the Ollama model when used in draft workflows.",
    )
    draft_temperature: float = Field(
        default=0.0,
        description="The temperature setting for the Ollama model when used in draft workflows.",
    )
    draft_mirostat: int = Field(
        default=0,
        description="The mirostat setting for the Ollama model when used in draft workflows.",
    )
    draft_mirostat_tau: float = Field(
        default=5.0,
        description="The mirostat_tau setting for the Ollama model when used in draft workflows.",
    )
    draft_mirostat_eta: float = Field(
        default=0.1,
        description="The mirostat_eta setting for the Ollama model when used in draft workflows.",
    )
    draft_num_predict: int = Field(
        default=128,
        description="The num_predict setting for the Ollama model when used in draft workflows.",
    )
    draft_repeat_last_n: int = Field(
        default=64,
        description="The repeat_last_n setting for the Ollama model when used in draft workflows.",
    )
    draft_repeat_penalty: float = Field(
        default=1.1,
        description="The repeat_penalty setting for the Ollama model when used in draft workflows.",
    )
    draft_seed: int | None = Field(
        default=None,
        description="The seed for the Ollama model when used in draft workflows. If None, a random seed will be used.",
    )
    draft_tfs_z: float = Field(
        default=1.0,
        description="The tfs_z setting for the Ollama model when used in draft workflows.",
    )
    draft_keep_alive: int | str | None = Field(
        default=None,
        description="The keepalive setting for the Ollama model when used in draft workflows. Can be an integer number of seconds or the string 'inf' for infinite keepalive.",
    )

    # review settings
    review_num_ctx: int = Field(
        default=2048,
        description="The context size for the Ollama model when used in review workflows.",
    )
    review_top_k: int = Field(
        default=40,
        description="The top_k setting for the Ollama model when used in review workflows.",
    )
    review_top_p: float = Field(
        default=0.9,
        description="The top_p setting for the Ollama model when used in review workflows.",
    )
    review_temperature: float = Field(
        default=0.0,
        description="The temperature setting for the Ollama model when used in review workflows.",
    )
    review_mirostat: int = Field(
        default=0,
        description="The mirostat setting for the Ollama model when used in review workflows.",
    )
    review_mirostat_tau: float = Field(
        default=5.0,
        description="The mirostat_tau setting for the Ollama model when used in review workflows.",
    )
    review_mirostat_eta: float = Field(
        default=0.1,
        description="The mirostat_eta setting for the Ollama model when used in review workflows.",
    )
    review_num_predict: int = Field(
        default=128,
        description="The num_predict setting for the Ollama model when used in review workflows.",
    )
    review_repeat_last_n: int = Field(
        default=64,
        description="The repeat_last_n setting for the Ollama model when used in review workflows.",
    )
    review_repeat_penalty: float = Field(
        default=1.1,
        description="The repeat_penalty setting for the Ollama model when used in review workflows.",
    )
    review_seed: int | None = Field(
        default=None,
        description="The seed for the Ollama model when used in review workflows. If None, a random seed will be used.",
    )
    review_tfs_z: float = Field(
        default=1.0,
        description="The tfs_z setting for the Ollama model when used in review workflows.",
    )
    review_keep_alive: int | str | None = Field(
        default=None,
        description="The keepalive setting for the Ollama model when used in review workflows. Can be an integer number of seconds or the string 'inf' for infinite keepalive.",
    )


class OllamaProvider(BaseLLMProvider):
    """
    Ollama LLM provider plugin for WayGate.
    """

    @staticmethod
    @hookimpl
    def waygate_llm_plugin() -> type[BaseLLMProvider]:
        return OllamaProvider

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        return PluginConfigRegistration(
            name=PLUGIN_NAME,
            config=OllamaProviderConfig,
        )

    def __init__(self):
        self._config = OllamaProviderConfig()

    @property
    def name(self) -> str:
        return PLUGIN_NAME

    @property
    def description(self) -> str:
        return "LLM provider plugin for Ollama."

    @property
    def version(self) -> str:
        return __version__

    def _get_params(self, workflow_type: str | None) -> dict:
        if workflow_type is None:
            return {
                "base_url": self._config.base_url,
                "temperature": 0.0,
                "top_k": 40,
                "top_p": 0.9,
                "num_ctx": 2048,
            }

        if workflow_type.lower() == "draft":
            return {
                "base_url": self._config.base_url,
                "temperature": self._config.draft_temperature,
                "top_k": self._config.draft_top_k,
                "top_p": self._config.draft_top_p,
                "num_ctx": self._config.draft_num_ctx,
                "mirostat": self._config.draft_mirostat,
                "mirostat_tau": self._config.draft_mirostat_tau,
                "mirostat_eta": self._config.draft_mirostat_eta,
                "num_predict": self._config.draft_num_predict,
                "repeat_last_n": self._config.draft_repeat_last_n,
                "repeat_penalty": self._config.draft_repeat_penalty,
                "seed": self._config.draft_seed,
                "tfs_z": self._config.draft_tfs_z,
                "keep_alive": self._config.draft_keep_alive,
            }
        elif workflow_type.lower() == "review":
            return {
                "base_url": self._config.base_url,
                "temperature": self._config.review_temperature,
                "top_k": self._config.review_top_k,
                "top_p": self._config.review_top_p,
                "num_ctx": self._config.review_num_ctx,
                "mirostat": self._config.review_mirostat,
                "mirostat_tau": self._config.review_mirostat_tau,
                "mirostat_eta": self._config.review_mirostat_eta,
                "num_predict": self._config.review_num_predict,
                "repeat_last_n": self._config.review_repeat_last_n,
                "repeat_penalty": self._config.review_repeat_penalty,
                "seed": self._config.review_seed,
                "tfs_z": self._config.review_tfs_z,
                "keep_alive": self._config.review_keep_alive,
            }
        else:
            return {
                "base_url": self._config.base_url,
                "temperature": 0.0,
                "top_k": 40,
                "top_p": 0.9,
                "num_ctx": 2048,
            }

    def get_llm(
        self,
        model_name: str,
        workflow_type: str | None = None,
    ) -> Runnable:
        """
        Retrieve an Ollama LLM instance by name.

        Args:
            model_name (str): The name of the Ollama model to retrieve.
            temperature (float): The temperature setting for the model.
            workflow_type (str | None): The type of workflow for which the LLM is being retrieved.

        Returns:
            ChatOllama: An instance of the requested Ollama LLM model.
        """
        params = self._get_params(workflow_type)
        llm = ChatOllama(model=model_name, **params)
        return llm

    def get_structured_llm(
        self,
        schema,
        model_name: str,
        workflow_type: str | None = None,
    ) -> Runnable:
        """
        Retrieve a structured Ollama LLM instance that outputs data conforming to the provided schema.

        Args:
            schema (Type[T]): A Pydantic model class that defines the expected output structure.
            model_name (str): The name of the Ollama model to retrieve.
            temperature (float): The temperature setting for the model.
            workflow_type (str | None): The type of workflow for which the LLM is being retrieved.

        Returns:
            ChatOllama: An instance of ChatOllama that will output data conforming to the provided schema.
        """
        params = self._get_params(workflow_type)
        llm = ChatOllama(model=model_name, **params)
        return llm.with_structured_output(schema)
