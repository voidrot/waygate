from waygate_conductor.clients import on_connect, on_message
import signal
import sys
import time
from contextlib import contextmanager

from waygate_conductor.registry import core_config
from waygate_api.clients import mqtt_client
from waygate_core.logging import configure_logging, get_logger

configure_logging()

logger = get_logger()

# Flag to track shutdown state
_shutdown_requested = False


def _handle_shutdown_signal(signum: int, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name}, initiating graceful shutdown...")
    _shutdown_requested = True


@contextmanager
def mqtt_connection():
    """Context manager for MQTT connection with guaranteed cleanup."""
    try:
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.connect(core_config.mqtt_host, core_config.mqtt_port)
        logger.info(
            f"Connected to MQTT broker at {core_config.mqtt_host}:{core_config.mqtt_port}"
        )
        # Start the background loop
        mqtt_client.loop_start()
        yield
    finally:
        logger.info("Stopping MQTT loop and disconnecting...")
        mqtt_client.loop_stop()
        # Wait briefly for loop to stop
        time.sleep(0.1)
        mqtt_client.disconnect()
        logger.info("MQTT client disconnected")


def setup_signal_handlers() -> None:
    """Register signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)


def main() -> None:
    logger.info("Starting WayGate Conductor MQTT Client...")
    setup_signal_handlers()

    with mqtt_connection():
        # Keep the main thread alive while listening for shutdown signals
        try:
            while not _shutdown_requested:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass

    logger.info("Graceful shutdown completed")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt, SystemExit:
        logger.info("Shutdown interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
