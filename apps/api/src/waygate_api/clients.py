from datetime import datetime, timezone
from uuid_utils import uuid4
from waygate_core.schema.graph_state import GraphStateRuntimeMetadata
from typing import List
from waygate_core.schema import GraphState
import paho.mqtt.client as mqtt

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)


def send_draft_message(raw_documents: List[str]) -> None:
    initial_state: GraphState = GraphState(
        task_objective="compile",
        source_documents=raw_documents,
        status="queued",
        runtime_metadata=GraphStateRuntimeMetadata(
            trace_id=str(uuid4()), enqueued_at=datetime.now(timezone.utc).isoformat()
        ),
    )
    mqtt_client.publish("waygate/drafts", payload=initial_state.model_dump_json())
