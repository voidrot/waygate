from waygate_core.file_templates import get_markdown_template, render_markdown_template


def test_get_markdown_template_returns_default_concepts_template() -> None:
    template = get_markdown_template()

    assert "## Summary" in template
    assert "$title" in template


def test_render_markdown_template_substitutes_title() -> None:
    rendered = render_markdown_template("WayGate Contract")

    assert rendered.startswith("# WayGate Contract")
    assert "## Key Details" in rendered
