from pathlib import Path

import pytest

from waygate_core.plugin.storage_base import StorageNamespace
from waygate_plugin_local_storage.plugin import LocalStorageProvider


@pytest.fixture
def provider(tmp_path: str, monkeypatch: pytest.MonkeyPatch) -> LocalStorageProvider:
    monkeypatch.setenv("WAYGATE_LOCAL_STORAGE_BASE_PATH", str(Path(tmp_path) / "wiki"))
    monkeypatch.chdir(Path(tmp_path))
    return LocalStorageProvider()


@pytest.mark.parametrize(
    ("namespace", "expected_dir_name"),
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
def test_build_namespaced_path_uses_storage_namespace_values(
    provider: LocalStorageProvider,
    namespace: StorageNamespace,
    expected_dir_name: str,
) -> None:
    path = provider.build_namespaced_path(namespace, "nested/document.md")

    assert path == f"{expected_dir_name}/nested/document.md"


def test_build_namespaced_path_rejects_already_namespaced_path(
    provider: LocalStorageProvider,
) -> None:
    with pytest.raises(ValueError, match="already be namespaced"):
        provider.build_namespaced_path(StorageNamespace.Raw, "raw/nested/document.md")


def test_build_path_returns_relative_path(
    provider: LocalStorageProvider,
) -> None:
    path = provider._build_path("raw/nested/document.md")

    assert path == Path("raw/nested/document.md")


def test_write_document_returns_file_uri(
    provider: LocalStorageProvider,
) -> None:
    uri = provider.write_document("raw/nested/document.md", "hello")

    assert uri.startswith("file://")


def test_write_document_accepts_storage_namespace_member(
    provider: LocalStorageProvider,
) -> None:
    provider.write_document(f"{StorageNamespace.Raw}/nested/document.md", "hello")

    assert Path("raw/nested/document.md").read_text() == "hello"


# --- prefix stripping ---


@pytest.mark.parametrize(
    ("document_path", "expected_suffix"),
    [
        ("file://test/path/file.md", "test/path/file.md"),
        ("file:///test/path/file.md", "test/path/file.md"),
        ("test/path/file.md", "test/path/file.md"),
    ],
)
def test_strip_prefix_removes_file_prefix(
    provider: LocalStorageProvider,
    document_path: str,
    expected_suffix: str,
) -> None:
    assert provider._strip_prefix(document_path) == expected_suffix


def test_build_path_strips_file_prefix(
    provider: LocalStorageProvider,
) -> None:
    path_with_prefix = provider._build_path(
        f"file://{StorageNamespace.Raw}/nested/document.md"
    )
    path_without_prefix = provider._build_path(
        f"{StorageNamespace.Raw}/nested/document.md"
    )

    assert path_with_prefix == path_without_prefix


def test_write_document_strips_file_prefix(
    provider: LocalStorageProvider,
) -> None:
    provider.write_document(
        f"file://{StorageNamespace.Raw}/nested/document.md", "hello"
    )

    assert Path("raw/nested/document.md").read_text() == "hello"
