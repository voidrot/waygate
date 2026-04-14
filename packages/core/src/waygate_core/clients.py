from celery import Celery
from waygate_core import get_app_context


def get_celery_client(client_name: str) -> Celery:
    app_context = get_app_context()

    return Celery(
        client_name,
        broker=app_context.config.core.celery_broker_dsn,
        backend=app_context.config.core.celery_result_backend_dsn,
    )
