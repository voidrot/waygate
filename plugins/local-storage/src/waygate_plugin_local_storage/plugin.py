from pydantic import BaseModel, Field
from waygate_core.plugin.hooks import PluginConfigRegistration, hookimpl
from waygate_core.plugin.storage import (
    StorageInvalidNamespaceError,
    StorageNamespace,
    StoragePlugin,
)

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

    def build_namespaced_path(
        self, namespace: StorageNamespace, document_path: str
    ) -> str:
        namespace_dirs = {
            StorageNamespace.Raw: self._config.raw_dir,
            StorageNamespace.Staging: self._config.staging_dir,
            StorageNamespace.Review: self._config.review_dir,
            StorageNamespace.Published: self._config.publish_dir,
            StorageNamespace.Metadata: self._config.metadata_dir,
            StorageNamespace.Templates: self._config.templates_dir,
            StorageNamespace.Agents: self._config.agents_dir,
        }

        try:
            base_dir = namespace_dirs[namespace]
        except KeyError as exc:
            raise StorageInvalidNamespaceError(
                f"Invalid storage namespace: {namespace}"
            ) from exc

        cleaned_document_path = document_path.lstrip("/")
        return f"{self._config.base_path}/{base_dir}/{cleaned_document_path}"

    def write_document(self, document_path: str, content: str) -> str:
        raise NotImplementedError

    def read_document(self, document_path: str) -> str:
        raise NotImplementedError

    def list_documents(self, search_path: str, prefix: str = "") -> list[str]:
        raise NotImplementedError

    def delete_document(self, document_path: str) -> None:
        raise NotImplementedError
