"""Unit tests for pure helper functions in compiler nodes.

Both ``_build_source_context`` (draft node) and ``_promote_from_raw``
(publish node) are free of I/O and LLM dependencies so they can be
tested directly without any mocking.
"""

from datetime import datetime, timezone
from compiler.nodes.draft import _build_source_context
from compiler.nodes.publish import _promote_from_raw
from waygate_core.schemas import RawDocument


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _raw(
    *,
    source_type: str = "web",
    source_id: str = "s1",
    source_url: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    doc = RawDocument.model_validate(
        {
            "source_type": source_type,
            "source_id": source_id,
            "timestamp": datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
            "content": "content",
            "tags": tags or [],
            "source_url": source_url,
        }
    )
    return doc.model_dump(mode="json")


# ---------------------------------------------------------------------------
# _build_source_context
# ---------------------------------------------------------------------------


class TestBuildSourceContext:
    def test_empty_list_returns_empty_string(self) -> None:
        assert _build_source_context([]) == ""

    def test_single_entry_wraps_in_xml_tags(self) -> None:
        raw = _raw(source_type="web")
        result = _build_source_context([raw])
        assert result.startswith("<source_context>")
        assert result.endswith("</source_context>")

    def test_source_type_always_present(self) -> None:
        raw = _raw(source_type="github")
        assert "[github]" in _build_source_context([raw])

    def test_source_url_included_when_present(self) -> None:
        raw = _raw(source_url="https://example.com/page")
        assert "https://example.com/page" in _build_source_context([raw])

    def test_source_url_omitted_when_none(self) -> None:
        raw = _raw(source_url=None)
        assert "http" not in _build_source_context([raw])

    def test_tags_included_when_present(self) -> None:
        raw = _raw(tags=["architecture", "langgraph"])
        result = _build_source_context([raw])
        assert "tags: architecture, langgraph" in result

    def test_tags_omitted_when_empty(self) -> None:
        raw = _raw(tags=[])
        assert "tags:" not in _build_source_context([raw])

    def test_multiple_entries_numbered_sequentially(self) -> None:
        docs = [_raw(source_type="web"), _raw(source_type="github", source_id="s2")]
        result = _build_source_context(docs)
        assert "  1." in result
        assert "  2." in result

    def test_separator_between_parts(self) -> None:
        raw = _raw(source_type="slack", source_url="https://slack.com/t/abc")
        result = _build_source_context([raw])
        assert "[slack] — https://slack.com/t/abc" in result


# ---------------------------------------------------------------------------
# _promote_from_raw
# ---------------------------------------------------------------------------


class TestPromoteFromRaw:
    def test_empty_list_returns_empty_tuples(self) -> None:
        result = _promote_from_raw([])
        assert result.lineage == []
        assert result.sources == []
        assert result.tags == []

    def test_lineage_contains_all_doc_ids(self) -> None:
        docs = [_raw(source_id="s1"), _raw(source_id="s2")]
        result = _promote_from_raw(docs)
        assert len(result.lineage) == 2

    def test_sources_contains_source_urls(self) -> None:
        docs = [
            _raw(source_url="https://a.com"),
            _raw(source_url="https://b.com", source_id="s2"),
        ]
        result = _promote_from_raw(docs)
        assert result.sources == ["https://a.com", "https://b.com"]

    def test_sources_skips_none_urls(self) -> None:
        docs = [_raw(source_url=None), _raw(source_url="https://x.com", source_id="s2")]
        result = _promote_from_raw(docs)
        assert result.sources == ["https://x.com"]

    def test_tags_aggregated_and_sorted(self) -> None:
        docs = [
            _raw(tags=["langgraph", "architecture"]),
            _raw(tags=["architecture", "fastapi"], source_id="s2"),
        ]
        result = _promote_from_raw(docs)
        assert result.tags == ["architecture", "fastapi", "langgraph"]

    def test_tags_deduplicated(self) -> None:
        docs = [_raw(tags=["a", "b"]), _raw(tags=["b", "c"], source_id="s2")]
        result = _promote_from_raw(docs)
        assert result.tags.count("b") == 1

    def test_empty_tags_on_all_docs_returns_empty(self) -> None:
        docs = [_raw(tags=[]), _raw(tags=[], source_id="s2")]
        result = _promote_from_raw(docs)
        assert result.tags == []

    def test_lineage_is_deduplicated_preserving_order(self) -> None:
        first = _raw(source_id="same")
        second = dict(first)
        result = _promote_from_raw([first, second])
        assert len(result.lineage) == 1
        assert result.lineage[0] == first["doc_id"]

    def test_sources_are_deduplicated_preserving_order(self) -> None:
        docs = [
            _raw(source_id="s1", source_url="https://dup.example"),
            _raw(source_id="s2", source_url="https://dup.example"),
            _raw(source_id="s3", source_url="https://unique.example"),
        ]
        result = _promote_from_raw(docs)
        assert result.sources == ["https://dup.example", "https://unique.example"]
