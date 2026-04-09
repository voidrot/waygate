from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

import frontmatter
from pydantic import BaseModel, Field

from compiler.config import storage
from compiler.state import GraphState
from waygate_core.schemas import AuditEvent, AuditEventType


class HumanReviewDecision(StrEnum):
    REVISE = "revise"
    APPROVE = "approve"
    REJECT = "reject"


class HumanReviewStatus(StrEnum):
    PENDING = "pending"
    FEEDBACK_RECORDED = "feedback_recorded"
    RESUMED = "resumed"
    CLOSED = "closed"


class HumanReviewRecord(BaseModel):
    review_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str
    updated_at: str
    trace_id: str | None = None
    target_topic: str
    staging_uri: str
    status: HumanReviewStatus | str = HumanReviewStatus.PENDING
    decision: HumanReviewDecision | str | None = None
    feedback: str | None = None
    revised_draft: str | None = None
    state_snapshot: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_to_markdown(record: HumanReviewRecord) -> str:
    post = frontmatter.Post("", **record.model_dump(mode="json"))
    return frontmatter.dumps(post)


def _record_from_markdown(content: str) -> HumanReviewRecord:
    post = frontmatter.loads(content)
    return HumanReviewRecord.model_validate(dict(post.metadata))


def _build_workflow_app():
    from compiler.graph import build_graph

    return build_graph()


def _publish_reviewed_draft(state: GraphState) -> dict[str, Any]:
    from compiler.nodes.publish import publish_node

    return publish_node(state)


def create_human_review_record(
    state: GraphState,
    staging_uri: str,
) -> tuple[HumanReviewRecord, str]:
    timestamp = _now_iso()
    record = HumanReviewRecord(
        created_at=timestamp,
        updated_at=timestamp,
        trace_id=state.get("trace_id"),
        target_topic=state["target_topic"],
        staging_uri=staging_uri,
        status=HumanReviewStatus.PENDING,
        state_snapshot=dict(state),
        payload={
            "revision_count": state.get("revision_count", 0),
            "new_document_uris": state.get("new_document_uris", []),
        },
    )
    uri = storage.write_meta_document(
        "human-review",
        record.review_id,
        _record_to_markdown(record),
    )
    return record, uri


def read_human_review_record(review_uri: str) -> HumanReviewRecord:
    return _record_from_markdown(storage.read_meta_document(review_uri))


def _write_human_review_record(record: HumanReviewRecord) -> str:
    return storage.write_meta_document(
        "human-review",
        record.review_id,
        _record_to_markdown(record),
    )


def submit_human_review_feedback(
    review_uri: str,
    *,
    decision: HumanReviewDecision | str,
    feedback: str,
    revised_draft: str | None = None,
) -> HumanReviewRecord:
    record = read_human_review_record(review_uri)
    if record.status != HumanReviewStatus.PENDING:
        raise ValueError("Human review feedback has already been recorded")

    normalized_decision = HumanReviewDecision(decision)
    record.status = HumanReviewStatus.FEEDBACK_RECORDED
    record.decision = normalized_decision
    record.feedback = feedback
    record.revised_draft = revised_draft
    record.updated_at = _now_iso()
    _write_human_review_record(record)

    storage.write_audit_event(
        AuditEvent(
            event_type=AuditEventType.COMPILER_HUMAN_REVIEW_FEEDBACK_RECORDED,
            occurred_at=record.updated_at,
            trace_id=record.trace_id,
            uris=[review_uri, record.staging_uri],
            payload={
                "decision": str(normalized_decision),
                "target_topic": record.target_topic,
            },
        )
    )
    return record


def resume_human_review(review_uri: str) -> dict[str, Any]:
    record = read_human_review_record(review_uri)
    if record.status != HumanReviewStatus.FEEDBACK_RECORDED:
        raise ValueError("Human review feedback must be recorded before resume")
    if record.decision is None:
        raise ValueError("Human review decision is missing")

    decision = HumanReviewDecision(record.decision)
    snapshot = GraphState(**record.state_snapshot)
    resumed_state: GraphState = {
        **snapshot,
        "staging_uri": record.staging_uri,
        "human_review_uri": review_uri,
    }

    if decision == HumanReviewDecision.REVISE:
        resumed_state["qa_feedback"] = record.feedback
        resumed_state["status"] = "pending_draft"
        resumed_state["revision_count"] = 0
        result = _build_workflow_app().invoke(resumed_state)
    elif decision == HumanReviewDecision.APPROVE:
        resumed_state["qa_feedback"] = record.feedback
        if record.revised_draft:
            resumed_state["current_draft"] = record.revised_draft
        result = {**resumed_state, **_publish_reviewed_draft(resumed_state)}
    else:
        record.status = HumanReviewStatus.CLOSED
        record.updated_at = _now_iso()
        record.payload = {**record.payload, "final_status": "human_rejected"}
        _write_human_review_record(record)
        return {
            **resumed_state,
            "status": "human_rejected",
        }

    record.status = HumanReviewStatus.RESUMED
    record.updated_at = _now_iso()
    record.payload = {**record.payload, "final_status": result.get("status")}
    _write_human_review_record(record)
    storage.write_audit_event(
        AuditEvent(
            event_type=AuditEventType.COMPILER_HUMAN_REVIEW_RESUMED,
            occurred_at=record.updated_at,
            trace_id=record.trace_id,
            uris=[review_uri, record.staging_uri],
            payload={
                "decision": str(decision),
                "final_status": result.get("status"),
                "target_topic": record.target_topic,
            },
        )
    )
    return result
