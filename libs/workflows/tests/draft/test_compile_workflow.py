from __future__ import annotations

from collections import deque
import importlib

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from waygate_workflows.agents.layout import CompileAgentRole
from waygate_workflows.agents.layout import DEFAULT_COMPILE_AGENT_LAYOUT
from waygate_workflows.schema import ContinuityExtractionModel
from waygate_workflows.schema import ContinuityMentionModel
from waygate_workflows.schema import DraftWorkflowStatus
from waygate_workflows.schema import DocumentAnalysisResultModel
from waygate_workflows.schema import FindingsExtractionModel
from waygate_workflows.schema import MetadataExtractionModel
from waygate_workflows.schema import ReviewOutcomeModel
from waygate_workflows.schema import SummaryExtractionModel
from waygate_workflows.schema import WorkflowEvent
from waygate_workflows.schema import WorkflowType
from waygate_workflows.tools.documents import derive_source_set_key
from waygate_workflows.workflows import compile as workflow_module

compile_source_document_module = importlib.import_module(
    "waygate_workflows.nodes.compile_source_document"
)
human_review_module = importlib.import_module("waygate_workflows.nodes.human_review")
normalize_request_module = importlib.import_module(
    "waygate_workflows.nodes.normalize_request"
)
source_normalization_module = importlib.import_module(
    "waygate_workflows.agents.source_normalization"
)
guidance_module = importlib.import_module("waygate_workflows.tools.guidance")
publish_module = importlib.import_module("waygate_workflows.nodes.publish")
review_module = importlib.import_module("waygate_workflows.nodes.review")
synthesis_module = importlib.import_module("waygate_workflows.nodes.synthesis")


class FakeStorage:
    def __init__(self, initial_documents: dict[str, str]) -> None:
        self.documents = dict(initial_documents)
        self.writes: list[tuple[str, str]] = []

    def build_namespaced_path(self, namespace, document_path: str) -> str:
        return f"{namespace.value}/{document_path}"

    def write_document(self, document_path: str, content: str) -> str:
        self.documents[document_path] = content
        self.writes.append((document_path, content))
        return f"file://{document_path}"

    def read_document(self, document_path: str) -> str:
        key = document_path.replace("file://", "")
        if document_path in self.documents:
            return self.documents[document_path]
        return self.documents[key]


class _FakeCoreSettings:
    metadata_model_name = "metadata-model"
    draft_model_name = "draft-model"
    review_model_name = "review-model"
    llm_workflow_profiles = {}
    llm_plugin_name = "fake-llm"


class _FakeAppContext:
    def __init__(self) -> None:
        self.config = type("Config", (), {"core": _FakeCoreSettings()})()
        self.plugins = type("Plugins", (), {"llm": {}})()


def _patch_storage(monkeypatch, storage: FakeStorage) -> None:
    monkeypatch.setattr(source_normalization_module, "resolve_storage", lambda: storage)
    monkeypatch.setattr(guidance_module, "resolve_storage", lambda: storage)
    monkeypatch.setattr(publish_module, "resolve_storage", lambda: storage)
    monkeypatch.setattr(human_review_module, "resolve_storage", lambda: storage)


def _patch_app_context(monkeypatch) -> None:
    monkeypatch.setattr(
        compile_source_document_module,
        "get_app_context",
        lambda: _FakeAppContext(),
    )
    monkeypatch.setattr(synthesis_module, "get_app_context", lambda: _FakeAppContext())
    monkeypatch.setattr(review_module, "get_app_context", lambda: _FakeAppContext())


def _make_initial_state(document_paths: list[str]) -> dict[str, object]:
    return {
        "workflow_type": WorkflowType.DRAFT,
        "event_type": WorkflowEvent.DRAFT_READY,
        "source": "test-suite",
        "raw_documents": document_paths,
        "source_documents": [],
        "document_order": [],
        "document_cursor": 0,
        "active_document": None,
        "source_set_key": None,
        "revision_count": 0,
        "status": DraftWorkflowStatus.READY,
        "scratchpad": {"terms": [], "claims": []},
        "extracted_metadata": [],
        "document_summaries": [],
        "prior_document_briefs": [],
        "canonical_topics": [],
        "canonical_tags": [],
        "glossary": [],
        "entity_registry": [],
        "claim_ledger": [],
        "reference_index": [],
        "unresolved_mentions": [],
        "current_draft": "",
        "review_feedback": [],
        "review_outcome": None,
        "published_document_uri": None,
        "published_document_id": None,
        "human_review_record_uri": None,
        "human_review_action": None,
    }


def test_derive_source_set_key_prefers_hashes_and_is_order_independent() -> None:
    documents_a = [
        {
            "uri": "a",
            "content": "A",
            "source_hash": "hash-b",
            "source_uri": "https://b",
            "source_type": None,
            "timestamp": None,
        },
        {
            "uri": "b",
            "content": "B",
            "source_hash": "hash-a",
            "source_uri": "https://a",
            "source_type": None,
            "timestamp": None,
        },
    ]
    documents_b = list(reversed(documents_a))

    assert derive_source_set_key(documents_a) == derive_source_set_key(documents_b)


def test_derive_source_set_key_rejects_mixed_identity_inputs() -> None:
    documents = [
        {
            "uri": "a",
            "content": "A",
            "source_hash": "hash-a",
            "source_uri": "https://a",
            "source_type": None,
            "timestamp": None,
        },
        {
            "uri": "b",
            "content": "B",
            "source_hash": None,
            "source_uri": "https://b",
            "source_type": None,
            "timestamp": None,
        },
    ]

    with pytest.raises(ValueError, match="source_hash coverage"):
        derive_source_set_key(documents)


def test_prompt_context_reconstructs_relevant_subsets() -> None:
    state = _make_initial_state(["file://raw/current.md"])
    state.update(
        {
            "document_cursor": 2,
            "prior_document_briefs": [
                {
                    "uri": "file://raw/brief-alpha.md",
                    "summary": "Alpha initiative brief",
                    "key_claims": ["Alpha launches next quarter"],
                    "defined_terms": ["Alpha"],
                    "discovered_topics": ["topic-one"],
                    "discovered_tags": ["tag-one"],
                    "referenced_entities": ["Alice"],
                    "supporting_source_uris": ["https://example.test/alpha"],
                },
                {
                    "uri": "file://raw/brief-gamma.md",
                    "summary": "Gamma archive",
                    "key_claims": ["Gamma was sunset"],
                    "defined_terms": ["Gamma"],
                    "discovered_topics": ["topic-zeta"],
                    "discovered_tags": ["tag-zeta"],
                    "referenced_entities": ["Bob"],
                    "supporting_source_uris": ["https://example.test/gamma"],
                },
            ],
            "canonical_topics": [
                {
                    "name": "topic-one",
                    "aliases": [],
                    "supporting_source_uris": ["https://example.test/alpha"],
                },
                {
                    "name": "topic-zeta",
                    "aliases": [],
                    "supporting_source_uris": ["https://example.test/gamma"],
                },
            ],
            "canonical_tags": [
                {
                    "name": "tag-one",
                    "aliases": [],
                    "supporting_source_uris": ["https://example.test/alpha"],
                },
                {
                    "name": "tag-zeta",
                    "aliases": [],
                    "supporting_source_uris": ["https://example.test/gamma"],
                },
            ],
            "glossary": [
                {
                    "term": "Alpha",
                    "aliases": [],
                    "definition_hint": None,
                    "supporting_source_uris": ["https://example.test/alpha"],
                },
                {
                    "term": "Gamma",
                    "aliases": [],
                    "definition_hint": None,
                    "supporting_source_uris": ["https://example.test/gamma"],
                },
            ],
            "entity_registry": [
                {
                    "kind": "person",
                    "canonical_name": "Alice",
                    "aliases": [],
                    "supporting_source_uris": ["https://example.test/alpha"],
                },
                {
                    "kind": "person",
                    "canonical_name": "Bob",
                    "aliases": [],
                    "supporting_source_uris": ["https://example.test/gamma"],
                },
            ],
            "claim_ledger": [
                {
                    "claim_id": "claim-alpha",
                    "text": "Alpha launches next quarter",
                    "supporting_source_uris": ["https://example.test/alpha"],
                    "related_entities": ["Alice"],
                    "related_terms": ["Alpha"],
                },
                {
                    "claim_id": "claim-gamma",
                    "text": "Gamma was sunset",
                    "supporting_source_uris": ["https://example.test/gamma"],
                    "related_entities": ["Bob"],
                    "related_terms": ["Gamma"],
                },
            ],
            "reference_index": [
                {
                    "key": "Alpha",
                    "kind": "term",
                    "source_uris": ["https://example.test/alpha"],
                    "processed_document_uris": ["file://raw/brief-alpha.md"],
                    "claim_ids": [],
                },
                {
                    "key": "Gamma",
                    "kind": "term",
                    "source_uris": ["https://example.test/gamma"],
                    "processed_document_uris": ["file://raw/brief-gamma.md"],
                    "claim_ids": [],
                },
            ],
            "unresolved_mentions": [
                {
                    "raw_text": "launch date",
                    "kind_hint": "claim",
                    "source_uri": "https://example.test/alpha",
                    "status": "open",
                },
                {
                    "raw_text": "legacy owner",
                    "kind_hint": "entity",
                    "source_uri": "https://example.test/gamma",
                    "status": "open",
                },
            ],
        }
    )

    prompt_context = (
        compile_source_document_module.build_document_analysis_prompt_context(
            state,
            {
                "uri": "file://raw/current.md",
                "content": "Alpha references Alice and the launch date.",
                "source_hash": "hash-current",
                "source_uri": "https://example.test/current",
                "source_type": "generic",
                "timestamp": None,
            },
        )
    )

    assert [entry["uri"] for entry in prompt_context["prior_briefs_subset"]] == [
        "file://raw/brief-alpha.md"
    ]
    assert [entry["name"] for entry in prompt_context["canonical_topics_subset"]] == [
        "topic-one"
    ]
    assert [entry["name"] for entry in prompt_context["canonical_tags_subset"]] == [
        "tag-one"
    ]
    assert [entry["term"] for entry in prompt_context["glossary_subset"]] == ["Alpha"]
    assert [entry["canonical_name"] for entry in prompt_context["entity_subset"]] == [
        "Alice"
    ]
    assert [entry["claim_id"] for entry in prompt_context["claim_subset"]] == [
        "claim-alpha"
    ]
    assert [entry["key"] for entry in prompt_context["reference_subset"]] == ["Alpha"]
    assert [
        entry["raw_text"] for entry in prompt_context["unresolved_mentions_subset"]
    ] == ["launch date"]


def test_prompt_context_loads_optional_agent_guidance(monkeypatch) -> None:
    storage = FakeStorage(
        {
            "agents/compile/source-analysis/common.md": "Prefer stable naming across documents.",
            "agents/compile/source-analysis/source-types/generic.md": "Treat generic sources as normalized reference material.",
        }
    )
    _patch_storage(monkeypatch, storage)

    prompt_context = (
        compile_source_document_module.build_document_analysis_prompt_context(
            _make_initial_state(["file://raw/current.md"]),
            {
                "uri": "file://raw/current.md",
                "content": "Generic document content.",
                "source_hash": "hash-current",
                "source_uri": "https://example.test/current",
                "source_type": "generic",
                "timestamp": None,
            },
        )
    )

    assert (
        "Prefer stable naming across documents."
        in prompt_context["prompt_instructions"]
    )
    assert (
        "Treat generic sources as normalized reference material."
        in prompt_context["prompt_instructions"]
    )


def test_compile_workflow_processes_documents_sequentially(monkeypatch) -> None:
    storage = FakeStorage(
        {
            "raw/one.md": "---\nsource_hash: hash-one\nsource_uri: https://example.test/one\nsource_type: generic\n---\nDocument one",
            "raw/two.md": "---\nsource_hash: hash-two\nsource_uri: https://example.test/two\nsource_type: generic\n---\nDocument two referencing Alpha and topic-one",
        }
    )
    summary_prompts: list[str] = []

    _patch_storage(monkeypatch, storage)
    _patch_app_context(monkeypatch)

    monkeypatch.setattr(
        compile_source_document_module,
        "analyze_source_document",
        lambda document, prompt_context, metadata_model_name, draft_model_name: (
            summary_prompts.append(str(prompt_context))
            or (
                DocumentAnalysisResultModel(
                    uri=str(document["uri"]),
                    metadata=MetadataExtractionModel(
                        tags=["tag-one"]
                        if str(document["uri"]) == "file://raw/one.md"
                        else ["tag-two"],
                        topics=["topic-one"]
                        if str(document["uri"]) == "file://raw/one.md"
                        else ["topic-two"],
                        people=["Alice"]
                        if str(document["uri"]) == "file://raw/one.md"
                        else [],
                        organizations=[]
                        if str(document["uri"]) == "file://raw/one.md"
                        else ["OrgX"],
                        projects=[],
                    ),
                    summary=SummaryExtractionModel(
                        summary="Summary one"
                        if str(document["uri"]) == "file://raw/one.md"
                        else "Summary two",
                    ),
                    findings=FindingsExtractionModel(
                        key_claims=["Claim A"]
                        if str(document["uri"]) == "file://raw/one.md"
                        else ["Claim B"],
                        defined_terms=["Alpha"]
                        if str(document["uri"]) == "file://raw/one.md"
                        else ["Beta"],
                    ),
                    continuity=ContinuityExtractionModel(
                        referenced_entities=[]
                        if str(document["uri"]) == "file://raw/one.md"
                        else ["Alice"],
                        unresolved_mentions=[]
                        if str(document["uri"]) == "file://raw/one.md"
                        else [
                            ContinuityMentionModel(
                                raw_text="the launch date",
                                kind_hint="claim",
                            )
                        ],
                    ),
                )
            )
        ),
    )
    monkeypatch.setattr(
        review_module,
        "review_draft_with_specialist",
        lambda state, review_model_name: ReviewOutcomeModel(approved=True, feedback=[]),
    )
    monkeypatch.setattr(
        synthesis_module,
        "synthesize_draft_with_specialist",
        lambda state, draft_model_name: "# Draft",
    )

    graph = workflow_module.compile_workflow(checkpointer=InMemorySaver())
    result = graph.invoke(
        _make_initial_state(["file://raw/one.md", "file://raw/two.md"]),
        config={"configurable": {"thread_id": "compile-test-1"}},
    )

    assert result["status"] == DraftWorkflowStatus.PUBLISHED
    assert result["document_cursor"] == 2
    assert result["published_document_id"] == result["source_set_key"]
    assert result["published_document_uri"].startswith("file://published/")
    assert len(result["prior_document_briefs"]) == 2
    assert [entry["term"] for entry in result["glossary"]] == ["Alpha", "Beta"]
    assert [entry["name"] for entry in result["canonical_topics"]] == [
        "topic-one",
        "topic-two",
    ]
    assert result["unresolved_mentions"] == [
        {
            "raw_text": "the launch date",
            "kind_hint": "claim",
            "source_uri": "https://example.test/two",
            "status": "open",
        }
    ]
    assert "Alpha" in summary_prompts[1]
    assert "topic-one" in summary_prompts[1]
    assert any(path.startswith("published/") for path, _ in storage.writes)


def test_compile_workflow_resolves_prior_unresolved_mentions(monkeypatch) -> None:
    storage = FakeStorage(
        {
            "raw/one.md": "---\nsource_hash: hash-one\nsource_uri: https://example.test/one\nsource_type: generic\n---\nDocument one mentions the launch date but does not define it.",
            "raw/two.md": "---\nsource_hash: hash-two\nsource_uri: https://example.test/two\nsource_type: generic\n---\nDocument two states the launch date is June 2026.",
        }
    )

    _patch_storage(monkeypatch, storage)
    _patch_app_context(monkeypatch)

    monkeypatch.setattr(
        compile_source_document_module,
        "analyze_source_document",
        lambda document, prompt_context, metadata_model_name, draft_model_name: (
            DocumentAnalysisResultModel(
                uri=str(document["uri"]),
                metadata=MetadataExtractionModel(
                    tags=[],
                    topics=["release-plan"],
                    people=[],
                    organizations=[],
                    projects=[],
                ),
                summary=SummaryExtractionModel(
                    summary="Document one summary"
                    if str(document["uri"]) == "file://raw/one.md"
                    else "Document two summary",
                ),
                findings=FindingsExtractionModel(
                    key_claims=[]
                    if str(document["uri"]) == "file://raw/one.md"
                    else ["The launch date is June 2026"],
                    defined_terms=[]
                    if str(document["uri"]) == "file://raw/one.md"
                    else ["launch date"],
                ),
                continuity=ContinuityExtractionModel(
                    referenced_entities=[],
                    unresolved_mentions=[
                        ContinuityMentionModel(
                            raw_text="launch date",
                            kind_hint="claim",
                        )
                    ]
                    if str(document["uri"]) == "file://raw/one.md"
                    else [],
                ),
            )
        ),
    )
    monkeypatch.setattr(
        review_module,
        "review_draft_with_specialist",
        lambda state, review_model_name: ReviewOutcomeModel(approved=True, feedback=[]),
    )
    monkeypatch.setattr(
        synthesis_module,
        "synthesize_draft_with_specialist",
        lambda state, draft_model_name: "# Draft",
    )

    graph = workflow_module.compile_workflow(checkpointer=InMemorySaver())
    result = graph.invoke(
        _make_initial_state(["file://raw/one.md", "file://raw/two.md"]),
        config={"configurable": {"thread_id": "compile-test-resolution"}},
    )

    assert result["status"] == DraftWorkflowStatus.PUBLISHED
    assert result["unresolved_mentions"] == [
        {
            "raw_text": "launch date",
            "kind_hint": "claim",
            "source_uri": "https://example.test/one",
            "status": "resolved",
        }
    ]


def test_compile_workflow_can_resume_from_human_review_to_publish(monkeypatch) -> None:
    storage = FakeStorage(
        {
            "raw/one.md": "---\nsource_hash: hash-one\nsource_uri: https://example.test/one\nsource_type: generic\n---\nDocument one",
        }
    )
    review_outcomes = deque(
        [
            ReviewOutcomeModel(approved=False, feedback=["rev-1"]),
            ReviewOutcomeModel(approved=False, feedback=["rev-2"]),
            ReviewOutcomeModel(approved=False, feedback=["rev-3"]),
        ]
    )

    _patch_storage(monkeypatch, storage)
    _patch_app_context(monkeypatch)

    monkeypatch.setattr(
        compile_source_document_module,
        "analyze_source_document",
        lambda document, prompt_context, metadata_model_name, draft_model_name: (
            DocumentAnalysisResultModel(
                uri=str(document["uri"]),
                metadata=MetadataExtractionModel(
                    tags=["tag"],
                    topics=["topic"],
                    people=[],
                    organizations=[],
                    projects=[],
                ),
                summary=SummaryExtractionModel(
                    summary="Summary",
                ),
                findings=FindingsExtractionModel(
                    key_claims=["claim"],
                    defined_terms=["term"],
                ),
            )
        ),
    )
    monkeypatch.setattr(
        review_module,
        "review_draft_with_specialist",
        lambda state, review_model_name: review_outcomes.popleft(),
    )
    monkeypatch.setattr(
        synthesis_module,
        "synthesize_draft_with_specialist",
        lambda state, draft_model_name: "# Draft",
    )

    graph = workflow_module.compile_workflow(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "compile-test-2"}}
    interrupted = graph.invoke(
        _make_initial_state(["file://raw/one.md"]), config=config
    )

    assert "__interrupt__" in interrupted
    assert any(path.startswith("review/") for path, _ in storage.writes)

    resumed = graph.invoke(
        Command(
            resume={"action": "resume_to_publish", "feedback": ["approved by human"]}
        ),
        config=config,
    )

    assert resumed["status"] == DraftWorkflowStatus.PUBLISHED
    assert resumed["published_document_uri"].startswith("file://published/")
    assert resumed["human_review_record_uri"].startswith("file://review/")
    assert "approved by human" in resumed["review_feedback"]


def test_default_compile_agent_layout_matches_design_doc_roles() -> None:
    assert [entry.role for entry in DEFAULT_COMPILE_AGENT_LAYOUT] == [
        CompileAgentRole.SOURCE_NORMALIZATION,
        CompileAgentRole.SOURCE_ANALYSIS,
        CompileAgentRole.SYNTHESIS,
        CompileAgentRole.REVIEW,
        CompileAgentRole.PUBLISH,
        CompileAgentRole.HUMAN_REVIEW,
    ]
    assert DEFAULT_COMPILE_AGENT_LAYOUT[1].execution_boundary == "agentic"
    assert DEFAULT_COMPILE_AGENT_LAYOUT[4].execution_boundary == "deterministic"
