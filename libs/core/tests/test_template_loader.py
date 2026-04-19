from datetime import datetime

import pytest

from waygate_core.files import template
from waygate_core.schema import RawDocument


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
    monkeypatch.setenv("WAYGATE_CORE__DRAFT_DOC_TEMPLATE", "custom_draft.j2")

    _clear_template_caches()
    packages, raw_template_name, draft_template_name = template._get_template_settings()

    assert packages == ("waygate_core", "waygate_plugin_communication_http")
    assert raw_template_name == "custom_raw.j2"
    assert draft_template_name == "custom_draft.j2"


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
        lambda: (("waygate_core",), "custom_raw.j2", "custom_draft.j2"),
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


def test_render_draft_document_uses_configured_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_template = _FakeTemplate()

    monkeypatch.setattr(
        template,
        "_get_template_settings",
        lambda: (("waygate_core",), "custom_raw.j2", "custom_draft.j2"),
    )
    monkeypatch.setattr(
        template,
        "_get_template",
        lambda packages, name: fake_template,
    )

    result = template.render_draft_document(
        context={"a": 1}, content="draft", doc_uri="raw/example.md"
    )

    assert result == "rendered-output"
    assert fake_template.render_calls[0]["content"] == "draft"
    assert fake_template.render_calls[0]["doc_uri"] == "raw/example.md"
