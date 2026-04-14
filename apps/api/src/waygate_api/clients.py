from waygate_core.tasks import new_draft
from waygate_core import get_celery_client
from datetime import datetime, timezone
from uuid_utils import uuid4
from waygate_core.schema.graph_state import GraphStateRuntimeMetadata
from typing import List
from waygate_core.schema import GraphState


celery_client = get_celery_client("waygate_api")


def send_draft_message(raw_documents: List[str]) -> None:
    initial_state: GraphState = GraphState(
        task_objective="compile",
        source_documents=raw_documents,
        status="queued",
        runtime_metadata=GraphStateRuntimeMetadata(
            trace_id=str(uuid4()), enqueued_at=datetime.now(timezone.utc).isoformat()
        ),
    )

    new_draft.delay(initial_state.model_dump())
