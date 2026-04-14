from waygate_core import init_app, get_celery_client

init_app()

app = get_celery_client("waygate_conductor")

app.autodiscover_tasks(["waygate_core.tasks"])
