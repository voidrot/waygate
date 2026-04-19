from __future__ import annotations

import hashlib
import json
from typing import Any

from waygate_core.logging import get_logger
from waygate_core.plugin import WorkflowTriggerMessage

logger = get_logger(__name__)


def process_workflow_trigger(payload: dict[str, Any] | str) -> dict[str, Any]:
    """Process a serialized workflow trigger payload from an RQ worker."""

    raw_payload = json.loads(payload) if isinstance(payload, str) else payload
    message = WorkflowTriggerMessage.model_validate(raw_payload)

    if message.event_type == "draft.ready":
        return trigger_draft_workflow_from_message(message)

    logger.info(
        "Ignoring unsupported workflow trigger event",
        event_type=message.event_type,
        source=message.source,
    )
    return {
        "status": "ignored",
        "event_type": message.event_type,
        "source": message.source,
        "reason": "No workflow handler is registered for this event type",
    }


def trigger_draft_workflow_from_message(
    message: WorkflowTriggerMessage,
) -> dict[str, Any]:
    """Return the already-written draft document URIs for workflow handoff."""

    if not message.document_paths:
        raise ValueError("draft.ready triggers require at least one document path")

    request_key = _build_request_key(message)

    logger.info(
        "Draft workflow trigger received",
        request_key=request_key,
        source=message.source,
        document_paths=list(message.document_paths),
    )

    return {
        "status": "triggered",
        "event_type": message.event_type,
        "source": message.source,
        "request_key": request_key,
        "document_paths": list(message.document_paths),
        "metadata": dict(message.metadata),
    }


def _build_request_key(message: WorkflowTriggerMessage) -> str:
    seed = message.idempotency_key or "|".join(sorted(message.document_paths))
    if not seed:
        seed = message.source
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
