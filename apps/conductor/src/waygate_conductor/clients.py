from waygate_conductor.workflow.compile import compile_graph
from waygate_core.schema import GraphState
from waygate_conductor.registry import core_config
from waygate_core.logging import get_logger
import paho.mqtt.client as mqtt

logger = get_logger()


def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info(f"Connected to MQTT broker successfully ({reason_code})")
    else:
        logger.error(f"Failed to connect to MQTT broker, return code {reason_code}")

    logger.info(f"Subscribing to topic '{core_config.mqtt_draft_topic}'")
    try:
        client.subscribe(core_config.mqtt_draft_topic)
        logger.info(
            f"Subscribed to topic '{core_config.mqtt_draft_topic}' successfully"
        )
    except Exception as e:
        logger.error(
            f"Failed to subscribe to topic '{core_config.mqtt_draft_topic}': {e}"
        )


def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    logger.info(
        f"Received message on topic '{msg.topic}' with payload: {msg.payload}. Userdata: {userdata}"
    )
    initial_state = GraphState.model_validate_json(msg.payload.decode("utf-8"))
    logger.debug(f"Parsed GraphState: {initial_state}")
    workflow = compile_graph()
    workflow.run(initial_state)


mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
