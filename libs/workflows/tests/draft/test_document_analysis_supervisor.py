from __future__ import annotations

import json

from waygate_workflows.agents.document_analysis import analyze_document_with_supervisor
from waygate_workflows.schema import ContinuityExtractionModel
from waygate_workflows.schema import ContinuityMentionModel
from waygate_workflows.schema import DocumentAnalysisResultModel
from waygate_workflows.schema import FindingsExtractionModel
from waygate_workflows.schema import MetadataExtractionModel
from waygate_workflows.schema import SummaryExtractionModel


def test_analyze_document_with_supervisor_uses_multiple_specialist_subagents(
    monkeypatch,
) -> None:
    create_agent_calls: list[dict[str, object]] = []
    invoked_payloads: list[tuple[str, str]] = []
    resolved_models: list[tuple[str, str, str | None]] = []
    document = {
        "uri": "file://raw/one.md",
        "content": "Document one referencing Alpha",
        "source_hash": "hash-one",
        "source_uri": "https://example.test/one",
        "source_type": "generic",
        "timestamp": None,
    }
    prompt_context = {
        "active_document": document,
        "active_document_position": 1,
        "canonical_topics_subset": [
            {
                "name": "topic-one",
                "aliases": [],
                "supporting_source_uris": ["https://example.test/zero"],
            }
        ],
        "canonical_tags_subset": [],
        "glossary_subset": [
            {
                "term": "Alpha",
                "aliases": [],
                "definition_hint": None,
                "supporting_source_uris": ["https://example.test/zero"],
            }
        ],
        "entity_subset": [],
        "claim_subset": [],
        "reference_subset": [],
        "prior_briefs_subset": [],
        "unresolved_mentions_subset": [],
        "prompt_instructions": ["Reuse prior compile context."],
    }

    class FakeAgent:
        def __init__(self, kind: str, tools: list[object] | None = None) -> None:
            self.kind = kind
            self.tools = tools or []

        def invoke(self, payload: dict[str, object]) -> dict[str, object]:
            message = payload["messages"][0]["content"]
            invoked_payloads.append((self.kind, str(message)))
            if self.kind == "metadata":
                return {
                    "structured_response": MetadataExtractionModel(
                        tags=["tag-one"],
                        topics=["topic-one"],
                        people=["Alice"],
                        organizations=[],
                        projects=[],
                    )
                }
            if self.kind == "summary":
                return {
                    "structured_response": SummaryExtractionModel(
                        summary="Summary one",
                    )
                }
            if self.kind == "findings":
                return {
                    "structured_response": FindingsExtractionModel(
                        key_claims=["Claim A"],
                        defined_terms=["Alpha"],
                    )
                }
            if self.kind == "continuity":
                return {
                    "structured_response": ContinuityExtractionModel(
                        referenced_entities=["Alice"],
                        unresolved_mentions=[
                            ContinuityMentionModel(
                                raw_text="the missing owner",
                                kind_hint="entity",
                            )
                        ],
                    )
                }

            tool_map = {tool.name: tool for tool in self.tools}
            metadata_json = tool_map["extract_document_metadata"].invoke({})
            summary_json = tool_map["summarize_document"].invoke({})
            findings_json = tool_map["extract_grounded_findings"].invoke({})
            continuity_json = tool_map["inspect_document_continuity"].invoke({})
            return {
                "structured_response": DocumentAnalysisResultModel(
                    uri=document["uri"],
                    metadata=json.loads(metadata_json),
                    summary=json.loads(summary_json),
                    findings=json.loads(findings_json),
                    continuity=json.loads(continuity_json),
                )
            }

    def fake_create_agent(
        *, model, tools=None, response_format=None, system_prompt=None
    ):
        create_agent_calls.append(
            {
                "tools": [] if tools is None else [tool.name for tool in tools],
                "system_prompt": system_prompt,
            }
        )
        if tools:
            return FakeAgent("supervisor", tools)
        if len(create_agent_calls) == 1:
            return FakeAgent("metadata")
        if len(create_agent_calls) == 2:
            return FakeAgent("summary")
        if len(create_agent_calls) == 3:
            return FakeAgent("findings")
        return FakeAgent("continuity")

    monkeypatch.setattr(
        "waygate_workflows.agents.document_analysis.create_agent",
        fake_create_agent,
    )

    def fake_resolve_chat_model(
        workflow_name: str,
        fallback_model_name: str,
        *,
        target_name: str | None = None,
        requires_structured_output: bool = False,
    ) -> object:
        resolved_models.append((workflow_name, fallback_model_name, target_name))
        return object()

    monkeypatch.setattr(
        "waygate_workflows.agents.document_analysis.resolve_chat_model",
        fake_resolve_chat_model,
    )

    result = analyze_document_with_supervisor(
        document,
        prompt_context,
        metadata_model_name="metadata-model",
        draft_model_name="draft-model",
    )

    assert result.uri == document["uri"]
    assert result.metadata.topics == ["topic-one"]
    assert result.findings.defined_terms == ["Alpha"]
    assert result.continuity.unresolved_mentions[0].raw_text == "the missing owner"
    assert create_agent_calls[4]["tools"] == [
        "extract_document_metadata",
        "summarize_document",
        "extract_grounded_findings",
        "inspect_document_continuity",
    ]
    assert [kind for kind, _ in invoked_payloads] == [
        "supervisor",
        "metadata",
        "summary",
        "findings",
        "continuity",
    ]
    assert "Document one referencing Alpha" in invoked_payloads[0][1]
    assert "topic-one" in invoked_payloads[1][1]
    assert "Alpha" in invoked_payloads[2][1]
    assert "Alpha" in invoked_payloads[3][1]
    assert "Alpha" in invoked_payloads[4][1]
    assert resolved_models == [
        ("compile", "metadata-model", "compile.source-analysis.metadata"),
        ("compile", "draft-model", "compile.source-analysis.summary"),
        ("compile", "draft-model", "compile.source-analysis.findings"),
        ("compile", "draft-model", "compile.source-analysis.continuity"),
        ("compile", "draft-model", "compile.source-analysis.supervisor"),
    ]
