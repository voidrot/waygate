from datetime import datetime

import pytest

from waygate_core.files import template
from waygate_core.schema import (
    CompiledDocument,
    PublishedDocument,
    RawDocument,
    SourceDocumentReference,
)


class _FakeTemplate:
    def __init__(self) -> None:
        self.render_calls: list[dict[str, object]] = []

    def render(self, **kwargs: object) -> str:
        self.render_calls.append(kwargs)
        return "rendered-output"


def _clear_template_caches() -> None:
    template._get_template_settings.cache_clear()
    template._build_template_env.cache_clear()
    template._get_template.cache_clear()


def test_get_template_settings_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "WAYGATE_CORE__TEMPLATE_PACKAGES",
        "waygate_core,waygate_plugin_communication_http",
    )
    monkeypatch.setenv("WAYGATE_CORE__RAW_DOC_TEMPLATE", "custom_raw.j2")
    monkeypatch.setenv("WAYGATE_CORE__COMPILED_DOC_TEMPLATE", "custom_compiled.j2")
    monkeypatch.setenv("WAYGATE_CORE__PUBLISHED_DOC_TEMPLATE", "custom_published.j2")

    _clear_template_caches()
    (
        packages,
        raw_template_name,
        compiled_template_name,
        published_template_name,
    ) = template._get_template_settings()

    assert packages == ("waygate_core", "waygate_plugin_communication_http")
    assert raw_template_name == "custom_raw.j2"
    assert compiled_template_name == "custom_compiled.j2"
    assert published_template_name == "custom_published.j2"


def test_build_template_env_raises_for_missing_packages() -> None:
    _clear_template_caches()

    with pytest.raises(RuntimeError, match="No templates loader"):
        template._build_template_env(("package_that_does_not_exist",))


def test_render_raw_document_uses_configured_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_template = _FakeTemplate()

    monkeypatch.setattr(
        template,
        "_get_template_settings",
        lambda: (
            ("waygate_core",),
            "custom_raw.j2",
            "custom_compiled.j2",
            "custom_published.j2",
        ),
    )
    monkeypatch.setattr(
        template,
        "_get_template",
        lambda packages, name: fake_template,
    )

    raw_doc = RawDocument(
        source_type="webhook",
        timestamp=datetime(2026, 1, 1),
        content="hello",
    )

    result = template.render_raw_document(raw_doc)

    assert result == "rendered-output"
    assert fake_template.render_calls[0]["raw_content"] == "hello"


def test_build_raw_document_frontmatter_populates_content_hash() -> None:
    raw_doc = RawDocument(
        source_type="webhook",
        content_type="markdown",
        timestamp=datetime(2026, 1, 1),
        content="hello",
    )

    frontmatter = template.build_raw_document_frontmatter(raw_doc)

    assert frontmatter.content_type == "text/markdown"
    assert frontmatter.content_hash == template.compute_content_hash("hello")


@pytest.mark.parametrize(
    ("content_type", "expected_content_type"),
    [
        ("markdown", "text/markdown"),
        (".json", "application/json"),
        ("TEXT/HTML", "text/html"),
        ("", None),
        (None, None),
    ],
)
def test_normalize_content_type(
    content_type: str | None,
    expected_content_type: str | None,
) -> None:
    assert template.normalize_content_type(content_type) == expected_content_type


@pytest.mark.parametrize(
    ("content", "expected_content_type"),
    [
        ("# Heading\n\nBody", "text/markdown"),
        ('{"hello": "world"}', "application/json"),
        ("<!DOCTYPE html><html><body>hello</body></html>", "text/html"),
        ("<?xml version='1.0'?><note>hello</note>", "application/xml"),
        ("hello world", "text/plain"),
    ],
)
def test_infer_content_type(content: str, expected_content_type: str) -> None:
    assert template.infer_content_type(content) == expected_content_type


def test_infer_content_type_prefers_source_uri_extension() -> None:
    assert (
        template.infer_content_type(
            '{"hello": "world"}',
            source_uri="https://example.test/files/document.md?download=1",
        )
        == "text/markdown"
    )


def test_infer_content_type_falls_back_to_source_id_extension() -> None:
    assert (
        template.infer_content_type("binary-ish content", source_id="report.pdf")
        == "application/pdf"
    )


def test_build_raw_document_frontmatter_infers_content_type_when_missing() -> None:
    raw_doc = RawDocument(
        source_type="webhook",
        source_uri="docs/meeting-notes.md",
        timestamp=datetime(2026, 1, 1),
        content="# Heading\n\nBody",
    )

    frontmatter = template.build_raw_document_frontmatter(raw_doc)

    assert frontmatter.content_type == "text/markdown"


def test_render_raw_document_preserves_body_verbatim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_template = _FakeTemplate()

    monkeypatch.setattr(
        template,
        "_get_template_settings",
        lambda: (
            ("waygate_core",),
            "custom_raw.j2",
            "custom_compiled.j2",
            "custom_published.j2",
        ),
    )
    monkeypatch.setattr(template, "_get_template", lambda packages, name: fake_template)

    raw_doc = RawDocument(
        source_type="webhook",
        timestamp=datetime(2026, 1, 1),
        content="<xml>hello</xml>",
    )

    template.render_raw_document(raw_doc)

    assert fake_template.render_calls[0]["raw_content"] == "<xml>hello</xml>"


def test_compute_content_hash_normalizes_line_endings_and_outer_whitespace() -> None:
    assert template.compute_content_hash(
        "\nhello\r\n"
    ) == template.compute_content_hash("hello\n")


def test_build_compiled_document_frontmatter() -> None:
    compiled_doc = CompiledDocument(
        doc_id="compiled-123",
        source_set_key="hash-source-set",
        source_documents=[
            SourceDocumentReference(
                uri="file://raw/one.txt",
                content_hash="content-one",
                source_hash="source-one",
                source_uri="https://example.test/one",
                source_type="generic",
                timestamp="2026-01-01T00:00:00Z",
            )
        ],
        compiled_at=datetime(2026, 1, 2),
        review_feedback=["looks good"],
        tags=["tag-one"],
        topics=["topic-one"],
        people=["Alice"],
        organizations=["WayGate"],
        projects=["WayGate Core"],
        content="# Compiled",
    )

    frontmatter = template.build_compiled_document_frontmatter(compiled_doc)

    assert frontmatter.doc_id == "compiled-123"
    assert frontmatter.source_documents == ["file://raw/one.txt"]
    assert frontmatter.source_content_hashes == ["content-one"]
    assert frontmatter.source_hashes == ["source-one"]
    assert frontmatter.source_uris == ["https://example.test/one"]
    assert frontmatter.review_feedback == ["looks good"]


def test_build_published_document_frontmatter() -> None:
    published_doc = PublishedDocument(
        doc_id="published-123",
        compiled_document_ids=["compiled-123"],
        compiled_document_uris=["file://compiled/compiled-123.md"],
        source_set_keys=["hash-source-set"],
        published_at=datetime(2026, 1, 3),
        tags=["tag-one"],
        topics=["topic-one"],
        people=["Alice"],
        organizations=["WayGate"],
        projects=["WayGate Core"],
        content="# Published",
    )

    frontmatter = template.build_published_document_frontmatter(published_doc)

    assert frontmatter.doc_id == "published-123"
    assert frontmatter.compiled_document_ids == ["compiled-123"]
    assert frontmatter.compiled_document_uris == ["file://compiled/compiled-123.md"]
    assert frontmatter.source_set_keys == ["hash-source-set"]


def test_render_compiled_document_uses_configured_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_template = _FakeTemplate()

    monkeypatch.setattr(
        template,
        "_get_template_settings",
        lambda: (
            ("waygate_core",),
            "custom_raw.j2",
            "custom_compiled.j2",
            "custom_published.j2",
        ),
    )
    monkeypatch.setattr(template, "_get_template", lambda packages, name: fake_template)

    compiled_doc = CompiledDocument(
        doc_id="compiled-123",
        source_set_key="hash-source-set",
        source_documents=[],
        compiled_at=datetime(2026, 1, 2),
        content="# Compiled",
    )

    result = template.render_compiled_document(compiled_doc)

    assert result == "rendered-output"
    assert fake_template.render_calls[0]["content"] == "# Compiled"
    assert "doc_id: compiled-123" in str(fake_template.render_calls[0]["frontmatter"])


def test_render_published_document_uses_configured_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_template = _FakeTemplate()

    monkeypatch.setattr(
        template,
        "_get_template_settings",
        lambda: (
            ("waygate_core",),
            "custom_raw.j2",
            "custom_compiled.j2",
            "custom_published.j2",
        ),
    )
    monkeypatch.setattr(template, "_get_template", lambda packages, name: fake_template)

    published_doc = PublishedDocument(
        doc_id="published-123",
        compiled_document_ids=["compiled-123"],
        compiled_document_uris=["file://compiled/compiled-123.md"],
        source_set_keys=["hash-source-set"],
        published_at=datetime(2026, 1, 3),
        content="# Published",
    )

    result = template.render_published_document(published_doc)

    assert result == "rendered-output"
    assert fake_template.render_calls[0]["content"] == "# Published"
    assert "doc_id: published-123" in str(fake_template.render_calls[0]["frontmatter"])
