from unittest.mock import MagicMock

from waygate_core.file_templates import (
    get_markdown_template,
    render_markdown_template,
    _load_template_from_storage,
)


def test_get_markdown_template_returns_default_concepts_template() -> None:
    template = get_markdown_template()

    assert "## Summary" in template
    assert "$title" in template


def test_render_markdown_template_substitutes_title() -> None:
    rendered = render_markdown_template("WayGate Contract")

    assert rendered.startswith("# WayGate Contract")
    assert "## Key Details" in rendered


def test_render_markdown_template_uses_packaged_default_when_storage_none() -> None:
    """Verify render_markdown_template falls back to packaged defaults when storage_provider is None."""
    rendered = render_markdown_template(
        "Test Title", document_type="concepts", storage_provider=None
    )

    assert "# Test Title" in rendered
    assert "## Summary" in rendered


def test_render_markdown_template_loads_from_storage_when_available() -> None:
    """Verify render_markdown_template attempts to load from storage when provider is available."""
    mock_storage = MagicMock()
    mock_storage.read_meta_document.return_value = "# $title\n\n## Custom Section"

    rendered = render_markdown_template(
        "Test Title", document_type="concepts", storage_provider=mock_storage
    )

    # Verify storage.read_meta_document was called with the correct URI
    mock_storage.read_meta_document.assert_called_once_with("meta/templates/concepts")
    # Verify the custom template was used
    assert "## Custom Section" in rendered
    assert "# Test Title" in rendered


def test_render_markdown_template_falls_back_to_packaged_when_storage_fails() -> None:
    """Verify render_markdown_template falls back to packaged defaults when storage read fails."""
    mock_storage = MagicMock()
    mock_storage.read_meta_document.side_effect = FileNotFoundError("Not found")

    rendered = render_markdown_template(
        "Test Title", document_type="concepts", storage_provider=mock_storage
    )

    # Should fall back to packaged template
    assert "# Test Title" in rendered
    assert "## Summary" in rendered


def test_load_template_from_storage_returns_none_when_provider_is_none() -> None:
    """Verify _load_template_from_storage returns None when storage_provider is None."""
    result = _load_template_from_storage(None, "concepts")
    assert result is None


def test_load_template_from_storage_constructs_correct_uri() -> None:
    """Verify _load_template_from_storage constructs the correct storage URI."""
    mock_storage = MagicMock()
    mock_storage.read_meta_document.return_value = "# $title\n\nCustom"

    result = _load_template_from_storage(mock_storage, "entities")

    mock_storage.read_meta_document.assert_called_once_with("meta/templates/entities")
    assert result is not None
    assert "Custom" in result


def test_load_template_from_storage_returns_none_on_error() -> None:
    """Verify _load_template_from_storage returns None when read fails."""
    mock_storage = MagicMock()
    mock_storage.read_meta_document.side_effect = Exception("Storage error")

    result = _load_template_from_storage(mock_storage, "concepts")

    assert result is None
