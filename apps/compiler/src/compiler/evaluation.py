from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from compiler.nodes import draft
from compiler.state import GraphState
from pydantic import BaseModel, Field
from waygate_core.schemas import DocumentType, RawDocument

DEFAULT_GOLDEN_DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "golden" / "compiler_golden_dataset.json"
)
CONVERSATIONAL_FILLER = (
    "certainly!",
    "here is the summary",
    "in conclusion",
    "let me know",
)


class GoldenRawDocument(BaseModel):
    source_type: str
    source_id: str
    timestamp: str
    content: str
    tags: list[str] = Field(default_factory=list)
    source_url: str | None = None


class MetricThresholds(BaseModel):
    grounding: float = 0.8
    relevance: float = 0.8
    markdown: float = 0.8


class GoldenCase(BaseModel):
    case_id: str
    description: str
    target_topic: str
    document_type: str = DocumentType.CONCEPTS.value
    raw_documents: list[GoldenRawDocument]
    expected_output: str
    required_snippets: list[str] = Field(default_factory=list)
    focus_terms: list[str] = Field(default_factory=list)
    forbidden_snippets: list[str] = Field(default_factory=list)
    thresholds: MetricThresholds = Field(default_factory=MetricThresholds)


class GoldenDataset(BaseModel):
    version: str
    description: str
    cases: list[GoldenCase]


class EvaluationMetrics(BaseModel):
    grounding: float
    relevance: float
    markdown: float


class EvaluationCaseResult(BaseModel):
    case_id: str
    passed: bool
    metrics: EvaluationMetrics
    failures: list[str] = Field(default_factory=list)
    candidate_output: str


class EvaluationSummary(BaseModel):
    passed: bool
    total_cases: int
    passed_cases: int
    failed_cases: int
    results: list[EvaluationCaseResult]


CandidateRunner = Callable[[GoldenCase], str]
LLMFactory = Callable[[GoldenCase], Any]


class _GoldenDatasetStorage:
    def __init__(self, documents_by_uri: dict[str, str]) -> None:
        self._documents_by_uri = documents_by_uri

    def read_raw_document(self, uri: str) -> str:
        return self._documents_by_uri[uri]

    def read_meta_document(self, uri: str) -> str:
        raise FileNotFoundError(uri)


def load_golden_dataset(path: str | Path | None = None) -> GoldenDataset:
    dataset_path = Path(path) if path is not None else DEFAULT_GOLDEN_DATASET_PATH
    return GoldenDataset.model_validate_json(dataset_path.read_text(encoding="utf-8"))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _score_grounding(case: GoldenCase, candidate_output: str) -> tuple[float, list[str]]:
    failures: list[str] = []
    normalized_output = _normalize(candidate_output)
    required = case.required_snippets
    if not required:
        score = 1.0
    else:
        matched = sum(1 for snippet in required if _normalize(snippet) in normalized_output)
        score = matched / len(required)
        if matched != len(required):
            failures.append("missing required grounded facts")

    forbidden_hits = [
        snippet for snippet in case.forbidden_snippets if _normalize(snippet) in normalized_output
    ]
    if forbidden_hits:
        failures.append("contains forbidden snippets")
        penalty = min(0.5, 0.25 * len(forbidden_hits))
        score = max(0.0, score - penalty)

    return score, failures


def _score_relevance(case: GoldenCase, candidate_output: str) -> tuple[float, list[str]]:
    failures: list[str] = []
    normalized_output = _normalize(candidate_output)
    focus_terms = case.focus_terms or [case.target_topic]
    matched_terms = sum(1 for term in focus_terms if _normalize(term) in normalized_output)
    focus_score = matched_terms / len(focus_terms)

    topic_slug = _normalize(case.target_topic)
    title_match = 1.0 if candidate_output.lstrip().startswith("#") and topic_slug in normalized_output else 0.0
    score = (focus_score + title_match) / 2

    if matched_terms != len(focus_terms):
        failures.append("missing focus terms")
    if title_match == 0.0:
        failures.append("missing topic-aligned markdown title")
    return score, failures


def _score_markdown(candidate_output: str) -> tuple[float, list[str]]:
    failures: list[str] = []
    checks = {
        "title": candidate_output.lstrip().startswith("# "),
        "section_headers": "## " in candidate_output,
        "balanced_code_fences": candidate_output.count("```") % 2 == 0,
        "no_filler": not any(filler in candidate_output.lower() for filler in CONVERSATIONAL_FILLER),
    }
    failures.extend(
        reason.replace("_", " ")
        for reason, passed in checks.items()
        if not passed
    )
    score = sum(1 for passed in checks.values() if passed) / len(checks)
    return score, failures


def evaluate_case(case: GoldenCase, candidate_output: str) -> EvaluationCaseResult:
    grounding_score, grounding_failures = _score_grounding(case, candidate_output)
    relevance_score, relevance_failures = _score_relevance(case, candidate_output)
    markdown_score, markdown_failures = _score_markdown(candidate_output)

    metrics = EvaluationMetrics(
        grounding=grounding_score,
        relevance=relevance_score,
        markdown=markdown_score,
    )
    failures = [
        *grounding_failures,
        *relevance_failures,
        *markdown_failures,
    ]
    passed = (
        grounding_score >= case.thresholds.grounding
        and relevance_score >= case.thresholds.relevance
        and markdown_score >= case.thresholds.markdown
    )

    return EvaluationCaseResult(
        case_id=case.case_id,
        passed=passed,
        metrics=metrics,
        failures=sorted(set(failures)),
        candidate_output=candidate_output,
    )


def evaluate_candidate(
    dataset: GoldenDataset,
    candidate_runner: CandidateRunner,
) -> EvaluationSummary:
    results = [
        evaluate_case(case, candidate_runner(case))
        for case in dataset.cases
    ]
    passed_cases = sum(1 for result in results if result.passed)
    total_cases = len(results)
    return EvaluationSummary(
        passed=passed_cases == total_cases,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=total_cases - passed_cases,
        results=results,
    )


def _build_state_for_case(case: GoldenCase) -> GraphState:
    raw_documents_metadata: list[dict[str, Any]] = []
    new_document_uris: list[str] = []
    for index, raw_document in enumerate(case.raw_documents, start=1):
        uri = f"eval://{case.case_id}/{index}"
        new_document_uris.append(uri)
        raw_documents_metadata.append(
            RawDocument.model_validate(
                {
                    "source_type": raw_document.source_type,
                    "source_id": raw_document.source_id,
                    "timestamp": raw_document.timestamp,
                    "content": raw_document.content,
                    "tags": raw_document.tags,
                    "source_url": raw_document.source_url,
                }
            ).model_dump(mode="json")
        )

    return {
        "state_version": "1",
        "trace_id": f"eval-{case.case_id}",
        "enqueued_at": "2026-04-09T00:00:00+00:00",
        "new_document_uris": new_document_uris,
        "raw_documents_metadata": raw_documents_metadata,
        "target_topic": case.target_topic,
        "document_type": case.document_type,
        "current_draft": None,
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "pending_draft",
    }


def build_draft_node_candidate(llm_factory: LLMFactory) -> CandidateRunner:
    def run_case(case: GoldenCase) -> str:
        state = _build_state_for_case(case)
        storage = _GoldenDatasetStorage(
            {
                uri: raw_document.content
                for uri, raw_document in zip(state["new_document_uris"], case.raw_documents, strict=False)
            }
        )

        original_storage = draft.storage
        original_get_llm = draft.get_llm
        try:
            draft.storage = storage
            draft.get_llm = lambda *_args: llm_factory(case)
            result = draft.draft_node(state)
        finally:
            draft.storage = original_storage
            draft.get_llm = original_get_llm

        output = result.get("current_draft")
        if not isinstance(output, str):
            raise ValueError(f"Draft node did not return a markdown draft for {case.case_id}")
        return output

    return run_case


def _build_live_candidate_runner(provider_name: str | None, model_name: str | None) -> CandidateRunner:
    from waygate_core.llm import get_llm

    resolved_provider = provider_name or draft.draft_provider
    resolved_model = model_name or draft.draft_model
    return build_draft_node_candidate(
        lambda _case: get_llm(resolved_provider, resolved_model)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the WayGate compiler golden dataset evaluation harness.")
    parser.add_argument("--dataset", default=str(DEFAULT_GOLDEN_DATASET_PATH))
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    args = parser.parse_args(argv)

    dataset = load_golden_dataset(args.dataset)
    summary = evaluate_candidate(
        dataset,
        _build_live_candidate_runner(args.provider, args.model),
    )

    print(json.dumps(summary.model_dump(mode="json"), indent=2))
    return 0 if summary.passed else 1


__all__ = [
    "DEFAULT_GOLDEN_DATASET_PATH",
    "EvaluationCaseResult",
    "EvaluationMetrics",
    "EvaluationSummary",
    "GoldenCase",
    "GoldenDataset",
    "GoldenRawDocument",
    "MetricThresholds",
    "build_draft_node_candidate",
    "evaluate_candidate",
    "evaluate_case",
    "load_golden_dataset",
    "main",
]