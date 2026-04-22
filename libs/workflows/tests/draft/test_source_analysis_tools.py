from __future__ import annotations

from waygate_workflows.tools import build_source_analysis_tools


def test_build_source_analysis_tools_returns_supervisor_tool_set() -> None:
    class FakeAgent:
        def __init__(self, name: str) -> None:
            self.name = name

        def invoke(self, payload: dict[str, object]) -> dict[str, object]:
            raise AssertionError(
                f"{self.name} should not be invoked during construction"
            )

    tools = build_source_analysis_tools(
        document_prompt="prompt",
        metadata_agent=FakeAgent("metadata"),
        summary_agent=FakeAgent("summary"),
        findings_agent=FakeAgent("findings"),
        continuity_agent=FakeAgent("continuity"),
    )

    assert [tool.name for tool in tools] == [
        "extract_document_metadata",
        "summarize_document",
        "extract_grounded_findings",
        "inspect_document_continuity",
    ]
