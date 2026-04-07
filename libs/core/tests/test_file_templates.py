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


# ---------------------------------------------------------------
# NEW: Template edge cases and fallback behavior
# ---------------------------------------------------------------


def test_render_markdown_template_with_special_characters_in_title() -> None:
    """Verify render_markdown_template handles special characters safely."""
    title = "Title: With (Special) & Characters!"
    rendered = render_markdown_template(title, "concepts")

    assert "Title: With (Special) & Characters!" in rendered
    assert rendered.startswith("# Title: With (Special) & Characters!")


def test_render_markdown_template_respects_document_type_selection() -> None:
    """Verify different document types use different templates."""
    concepts_render = render_markdown_template("Test", document_type="concepts")
    entities_render = render_markdown_template("Test", document_type="entities")
    thematic_render = render_markdown_template("Test", document_type="thematic")

    # Each should have the type-specific section
    assert "## Summary" in concepts_render
    assert "## Responsibilities" not in concepts_render

    assert "## Overview" in entities_render
    assert "## Responsibilities" in entities_render

    assert "## Major Themes" in thematic_render
    assert "## Open Questions" in thematic_render


def test_render_markdown_template_fallback_chain_on_multiple_storage_failures() -> None:
    """Verify fallback to packaged template when storage fails multiple times."""
    mock_storage = MagicMock()
    mock_storage.read_meta_document.side_effect = [
        FileNotFoundError(),  # First call fails
        Exception("Connection error"),  # Any exception should trigger fallback
    ]

    # First call: storage fails, uses packaged
    result1 = render_markdown_template("Title 1", "concepts", mock_storage)
    assert "## Summary" in result1

    # Second call: storage fails again, uses packaged
    result2 = render_markdown_template("Title 2", "concepts", mock_storage)
    assert "## Summary" in result2


def test_render_markdown_template_empty_title_substitution() -> None:
    """Verify render_markdown_template handles empty title gracefully."""
    rendered = render_markdown_template("", "concepts")

    assert rendered.startswith("# ")
    assert "## Summary" in rendered


def test_get_markdown_template_unknown_document_type_falls_back_to_concepts() -> None:
    """Verify unknown document types fall back to CONCEPTS template."""
    result = get_markdown_template("unknown_type_xyz")

    # Should fall back to concepts template
    assert "## Summary" in result
