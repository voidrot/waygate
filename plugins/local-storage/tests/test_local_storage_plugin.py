import pytest

from waygate_core.plugin.storage import StorageInvalidNamespaceError, StorageNamespace
from waygate_plugin_local_storage.plugin import LocalStorageConfig, LocalStoragePlugin


@pytest.mark.parametrize(
    "namespace,expected_segment",
    [
        (StorageNamespace.Raw, "raw"),
        (StorageNamespace.Staging, "staging"),
        (StorageNamespace.Review, "review"),
        (StorageNamespace.Published, "published"),
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


def test_write_and_read_document_round_trip(tmp_path) -> None:
    plugin = LocalStoragePlugin(config=LocalStorageConfig(base_path=str(tmp_path)))
    document_path = plugin.build_namespaced_path(StorageNamespace.Raw, "docs/one.md")

    uri = plugin.write_document(document_path, "hello world")

    assert uri == "file://raw/docs/one.md"
    assert plugin.read_document(uri) == "hello world"


def test_list_documents_returns_file_uris(tmp_path) -> None:
    plugin = LocalStoragePlugin(config=LocalStorageConfig(base_path=str(tmp_path)))
    first_path = plugin.build_namespaced_path(StorageNamespace.Raw, "docs/one.md")
    second_path = plugin.build_namespaced_path(StorageNamespace.Raw, "docs/two.md")
    plugin.write_document(first_path, "one")
    plugin.write_document(second_path, "two")

    listed = plugin.list_documents(
        plugin.build_namespaced_path(StorageNamespace.Raw, "docs")
    )

    assert listed == ["file://raw/docs/one.md", "file://raw/docs/two.md"]


def test_delete_document_removes_file(tmp_path) -> None:
    plugin = LocalStoragePlugin(config=LocalStorageConfig(base_path=str(tmp_path)))
    document_path = plugin.build_namespaced_path(StorageNamespace.Raw, "docs/one.md")
    uri = plugin.write_document(document_path, "hello world")

    plugin.delete_document(uri)

    assert (
        plugin.list_documents(
            plugin.build_namespaced_path(StorageNamespace.Raw, "docs")
        )
        == []
    )
