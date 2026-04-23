from __future__ import annotations

import json

from waygate_workflows.agents.document_analysis import analyze_document_with_supervisor
from waygate_workflows.schema import ContinuityExtractionModel
from waygate_workflows.schema import ContinuityMentionModel
from waygate_workflows.schema import DocumentAnalysisResultModel
from waygate_workflows.schema import FindingsExtractionModel
from waygate_workflows.schema import MetadataExtractionModel
from waygate_workflows.schema import SummaryExtractionModel


class _RecordingLogger:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def debug(self, event: str, **kwargs: object) -> None:
        self.records.append({"level": "debug", "event": event, **kwargs})

    def info(self, event: str, **kwargs: object) -> None:
        self.records.append({"level": "info", "event": event, **kwargs})

    def warning(self, event: str, **kwargs: object) -> None:
        self.records.append({"level": "warning", "event": event, **kwargs})

    def error(self, event: str, **kwargs: object) -> None:
        self.records.append({"level": "error", "event": event, **kwargs})

    def has_event(self, level: str, event: str) -> bool:
        return any(
            record["level"] == level and record["event"] == event
            for record in self.records
        )


def test_analyze_document_with_supervisor_uses_multiple_specialist_subagents(
    monkeypatch,
) -> None:
    logger = _RecordingLogger()

    monkeypatch.setattr("waygate_workflows.agents.document_analysis.logger", logger)
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
        return FakeAgent("supervisor", tools)

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
    monkeypatch.setattr(
        "waygate_workflows.agents.document_analysis.invoke_structured_stage",
        lambda *, schema, workflow_name, fallback_model_name, target_name=None, system_prompt, user_prompt: (
            resolved_models.append((workflow_name, fallback_model_name, target_name))
            or (
                MetadataExtractionModel(
                    tags=["tag-one"],
                    topics=["topic-one"],
                    people=["Alice"],
                    organizations=[],
                    projects=[],
                )
                if schema is MetadataExtractionModel
                else SummaryExtractionModel(summary="Summary one")
                if schema is SummaryExtractionModel
                else FindingsExtractionModel(
                    key_claims=["Claim A"],
                    defined_terms=["Alpha"],
                )
                if schema is FindingsExtractionModel
                else ContinuityExtractionModel(
                    referenced_entities=["Alice"],
                    unresolved_mentions=[
                        ContinuityMentionModel(
                            raw_text="the missing owner",
                            kind_hint="entity",
                        )
                    ],
                )
            )
        ),
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
    assert create_agent_calls[0]["tools"] == [
        "extract_document_metadata",
        "summarize_document",
        "extract_grounded_findings",
        "inspect_document_continuity",
    ]
    assert [kind for kind, _ in invoked_payloads] == ["supervisor"]
    assert "Document one referencing Alpha" in invoked_payloads[0][1]
    assert resolved_models == [
        ("compile", "draft-model", "compile.source-analysis.supervisor"),
        ("compile", "metadata-model", "compile.source-analysis.metadata"),
        ("compile", "draft-model", "compile.source-analysis.summary"),
        ("compile", "draft-model", "compile.source-analysis.findings"),
        ("compile", "draft-model", "compile.source-analysis.continuity"),
    ]
    assert logger.has_event("info", "Starting document analysis supervisor run")
    assert logger.has_event("info", "Completed document analysis supervisor run")


def test_analyze_document_with_supervisor_falls_back_when_supervisor_lacks_structured_response(
    monkeypatch,
) -> None:
    invoked_kinds: list[str] = []
    logger = _RecordingLogger()

    monkeypatch.setattr("waygate_workflows.agents.document_analysis.logger", logger)
    document = {
        "uri": "file://raw/fallback.md",
        "content": "Document fallback content referencing Beta",
        "source_hash": "hash-fallback",
        "source_uri": "https://example.test/fallback",
        "source_type": "generic",
        "timestamp": None,
    }
    prompt_context = {
        "active_document": document,
        "active_document_position": 1,
        "canonical_topics_subset": [],
        "canonical_tags_subset": [],
        "glossary_subset": [],
        "entity_subset": [],
        "claim_subset": [],
        "reference_subset": [],
        "prior_briefs_subset": [],
        "unresolved_mentions_subset": [],
        "prompt_instructions": [],
    }

    class FakeSupervisor:
        def invoke(self, payload: dict[str, object]) -> dict[str, object]:
            invoked_kinds.append("supervisor")
            return {"messages": []}

    monkeypatch.setattr(
        "waygate_workflows.agents.document_analysis.create_agent",
        lambda **kwargs: FakeSupervisor(),
    )
    monkeypatch.setattr(
        "waygate_workflows.agents.document_analysis.resolve_chat_model",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        "waygate_workflows.agents.document_analysis.invoke_structured_stage",
        lambda *, schema, workflow_name, fallback_model_name, target_name=None, system_prompt, user_prompt: (
            invoked_kinds.append(str(target_name))
            or (
                MetadataExtractionModel(
                    tags=["tag-fallback"],
                    topics=["topic-fallback"],
                    people=[],
                    organizations=[],
                    projects=[],
                )
                if schema is MetadataExtractionModel
                else SummaryExtractionModel(summary="Fallback summary")
                if schema is SummaryExtractionModel
                else FindingsExtractionModel(
                    key_claims=["Claim fallback"],
                    defined_terms=["Beta"],
                )
                if schema is FindingsExtractionModel
                else ContinuityExtractionModel(
                    referenced_entities=["Beta"],
                    unresolved_mentions=[],
                )
            )
        ),
    )

    result = analyze_document_with_supervisor(
        document,
        prompt_context,
        metadata_model_name="metadata-model",
        draft_model_name="draft-model",
    )

    assert result.uri == document["uri"]
    assert result.metadata.tags == ["tag-fallback"]
    assert result.summary.summary == "Fallback summary"
    assert result.findings.defined_terms == ["Beta"]
    assert result.continuity.referenced_entities == ["Beta"]
    assert invoked_kinds == [
        "supervisor",
        "compile.source-analysis.metadata",
        "compile.source-analysis.summary",
        "compile.source-analysis.findings",
        "compile.source-analysis.continuity",
    ]
    assert logger.has_event(
        "warning",
        "Document analysis supervisor returned no structured response; falling back to direct specialists",
    )
