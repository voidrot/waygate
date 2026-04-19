from pydantic import BaseModel, Field
from waygate_core.plugin.hooks import PluginConfigRegistration, hookimpl
from waygate_core.plugin.storage import StoragePlugin

PLUGIN_NAME = "local-storage"


class LocalStorageConfig(BaseModel):
    base_path: str = Field(default="wiki")
    raw_dir: str = Field(default="raw")
    staging_dir: str = Field(default="staging")
    review_dir: str = Field(default="review")
    publish_dir: str = Field(default="publish")
    metadata_dir: str = Field(default="metadata")
    templates_dir: str = Field(default="templates")
    agents_dir: str = Field(default="agents")
    soft_delete: bool = Field(default=False)


class LocalStoragePlugin(StoragePlugin):
    plugin_name = PLUGIN_NAME

    def __init__(self, config: LocalStorageConfig | None = None) -> None:
        self._config = config or LocalStorageConfig()

    @staticmethod
    @hookimpl
    def waygate_storage_plugin() -> type["LocalStoragePlugin"]:
        return LocalStoragePlugin

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        return PluginConfigRegistration(name=PLUGIN_NAME, config=LocalStorageConfig)

    def write_document(self, document_path: str, content: str) -> str:
        raise NotImplementedError

    def read_document(self, document_path: str) -> str:
        raise NotImplementedError

    def list_documents(self, search_path: str, prefix: str = "") -> list[str]:
        raise NotImplementedError

    def delete_document(self, document_path: str) -> None:
        raise NotImplementedError
