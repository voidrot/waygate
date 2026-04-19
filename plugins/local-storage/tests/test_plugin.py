import pytest

from waygate_core.plugin.storage import StorageInvalidNamespaceError, StorageNamespace
from waygate_plugin_local_storage.plugin import LocalStorageConfig, LocalStoragePlugin


@pytest.mark.parametrize(
    "namespace,expected_segment",
    [
        (StorageNamespace.Raw, "raw"),
        (StorageNamespace.Staging, "staging"),
        (StorageNamespace.Review, "review"),
        (StorageNamespace.Published, "publish"),
        (StorageNamespace.Metadata, "metadata"),
        (StorageNamespace.Templates, "templates"),
        (StorageNamespace.Agents, "agents"),
    ],
)
def test_build_namespaced_path_uses_expected_subdirectory(
    namespace: StorageNamespace,
    expected_segment: str,
) -> None:
    plugin = LocalStoragePlugin(config=LocalStorageConfig(base_path="wiki"))

    result = plugin.build_namespaced_path(namespace, "/docs/one.md")

    assert result == f"wiki/{expected_segment}/docs/one.md"


def test_build_namespaced_path_raises_for_invalid_namespace() -> None:
    plugin = LocalStoragePlugin()

    with pytest.raises(StorageInvalidNamespaceError, match="Invalid storage namespace"):
        plugin.build_namespaced_path("bad-namespace", "doc.md")  # type: ignore[arg-type]
