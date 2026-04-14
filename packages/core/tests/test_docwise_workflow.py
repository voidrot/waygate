from datetime import datetime, timezone
from types import SimpleNamespace

from waygate_core.nodes.draft import draft_node
from waygate_core.nodes.metadata import metadata_node
from waygate_core.nodes.review import review_node
from waygate_core.nodes import utils as node_utils
from waygate_core.schema import DraftGraphState
from waygate_core.schema.document import (
    DraftGenerationResult,
    DraftMergeResult,
    MetadataExtractionResult,
)
from waygate_core.schema.graph_state import DraftGraphStateRuntimeMetadata
from waygate_core.workflow.compile import compile_graph


class FakeStorage:
    def __init__(self, documents: dict[str, str]) -> None:
        self._documents = documents

    def read_document(self, document_path: str) -> str:
        return self._documents[document_path]

    def build_namespaced_path(self, namespace, document_path: str) -> str:
        cleaned = document_path.lstrip("/")
        if cleaned.startswith(f"{namespace}/"):
            raise ValueError("already namespaced")
        return f"{namespace}/{cleaned}"

    def write_document(self, document_path: str, content: str) -> str:
        self._documents[document_path] = content
        return f"file://{document_path}"


class FakeStructuredRunnable:
    def __init__(self, schema: type, responses: dict[str, dict[str, object]]) -> None:
        self._schema = schema
        self._responses = responses

    def invoke(self, prompt: str):
        prompt_key = "doc-1"
        if "doc-2" in prompt:
            prompt_key = "doc-2"
        if self._schema is DraftMergeResult:
            prompt_key = "merge"

        return self._schema.model_validate(self._responses[prompt_key])


class FakeLLMProvider:
    def __init__(self) -> None:
        self._responses = {
            MetadataExtractionResult: {
                "doc-1": {
                    "topics": ["knowledge capture"],
                    "tags": ["alpha"],
                    "people": ["Alice Example"],
                    "organizations": ["Acme Corp"],
                    "projects": ["WayGate"],
                    "established_terms": ["context graph"],
                    "summary": "Alpha metadata summary",
                },
                "doc-2": {
                    "topics": ["review workflow"],
                    "tags": ["beta"],
                    "people": ["Bob Example", "Alice Example"],
                    "organizations": ["Acme Corp", "Beta Labs"],
                    "projects": ["WayGate", "Compiler"],
                    "established_terms": ["short term memory"],
                    "summary": "Beta metadata summary",
                },
            },
            DraftGenerationResult: {
                "doc-1": {
                    "content": "Alpha fragment with Alice Example and context graph.",
                    "summary": "Alpha fragment summary",
                },
                "doc-2": {
                    "content": "Beta fragment with Bob Example and short term memory.",
                    "summary": "Beta fragment summary",
                },
            },
            DraftMergeResult: {
                "merge": {
                    "content": "Merged KB draft covering Alice Example, Bob Example, Acme Corp, and Compiler review workflow.",
                }
            },
        }

    def get_structured_llm(
        self, schema, model_name: str, workflow_type: str | None = None
    ):
        return FakeStructuredRunnable(schema, self._responses[schema])


def build_state() -> DraftGraphState:
    return DraftGraphState(
        task_objective="compile",
        source_documents=["raw/doc-1.md", "raw/doc-2.md"],
        status="queued",
        runtime_metadata=DraftGraphStateRuntimeMetadata(
            trace_id="trace-1",
            enqueued_at=datetime.now(timezone.utc).isoformat(),
        ),
    )


def install_fake_runtime(monkeypatch) -> None:
    documents = {
        "raw/doc-1.md": "---\nsource_type: manual\nsource_id: doc-1\ntopics:\n  - alpha-seed\ntags:\n  - seeded\n---\nAlpha source body about Alice Example and context graph.",
        "raw/doc-2.md": "---\nsource_type: manual\nsource_id: doc-2\ntopics:\n  - beta-seed\ntags:\n  - seeded\n---\nBeta source body about Bob Example and review workflow.",
    }
    app_context = SimpleNamespace(
        config=SimpleNamespace(
            core=SimpleNamespace(
                storage_plugin_name="fake-storage",
                llm_plugin_name="fake-llm",
                metadata_model_name="metadata-test",
                draft_model_name="draft-test",
                review_model_name="review-test",
            )
        ),
        plugins=SimpleNamespace(
            storage={"fake-storage": FakeStorage(documents)},
            llm={"fake-llm": FakeLLMProvider()},
        ),
    )

    monkeypatch.setattr(node_utils, "get_app_context", lambda: app_context)


def test_docwise_metadata_and_draft_nodes_merge_into_single_review_document(
    monkeypatch,
) -> None:
    install_fake_runtime(monkeypatch)
    state = build_state()

    metadata_state = metadata_node(state)

    assert metadata_state.topics == [
        "alpha-seed",
        "knowledge capture",
        "beta-seed",
        "review workflow",
    ]
    assert metadata_state.tags == ["seeded", "alpha", "beta"]
    assert metadata_state.people == ["Alice Example", "Bob Example"]
    assert metadata_state.organizations == ["Acme Corp", "Beta Labs"]
    assert metadata_state.projects == ["WayGate", "Compiler"]
    assert len(metadata_state.document_metadata) == 2

    draft_state = draft_node(metadata_state)

    assert len(draft_state.draft_fragments) == 2
    assert draft_state.current_draft is not None
    assert draft_state.current_draft.startswith("Merged KB draft")
    assert len(draft_state.current_documents) == 1
    assert draft_state.current_documents[0].sources == ["raw/doc-1.md", "raw/doc-2.md"]

    review_state = review_node(draft_state)

    assert review_state.status == "approved"
    assert review_state.review_feedback is None


def test_compile_graph_runs_metadata_draft_and_review_docwise(monkeypatch) -> None:
    install_fake_runtime(monkeypatch)
    graph = compile_graph().compile()

    result = graph.invoke(build_state())
    final_state = DraftGraphState.model_validate(result)

    assert final_state.status == "published"
    assert final_state.current_draft is not None
    assert "Compiler review workflow" in final_state.current_draft
    assert final_state.people == ["Alice Example", "Bob Example"]
    assert len(final_state.current_documents) == 1
    assert final_state.final_drafts == [
        "file://published/compiler/trace-1/merged-draft.md"
    ]
    assert (
        final_state.published_metadata_uri
        == "file://metadata/compiler/trace-1/merged-metadata.json"
    )
