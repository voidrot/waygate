from uuid import uuid7
from waygate_core import get_app_context
from waygate_api.routes.webhooks.router import app_context
from waygate_core.workflow.compile import compile_graph
from waygate_core.schema import DraftGraphState
from celery.utils.log import get_task_logger
from waygate_core.logging.helpers import get_wrapped_logger
from celery import shared_task
from langgraph.checkpoint.postgres import PostgresSaver  # ty:ignore[unresolved-import]

logger = get_wrapped_logger(get_task_logger(__name__))

app_context = get_app_context()

core_config = app_context.config.core


@shared_task(pydantic=True)
def new_draft(initial_state: DraftGraphState) -> None:
    job_id = str(uuid7())
    logger.info(
        "Starting new draft task", num_documents=len(initial_state.source_documents)
    )
    with PostgresSaver.from_conn_string(
        f"postgresql://{core_config.pg_user}:{core_config.pg_password}@{core_config.pg_host}:{core_config.pg_port}/{core_config.pg_db}"
    ) as saver:
        saver.save_initial_state(initial_state)
        compile_workflow = compile_graph().compile(checkpointer=saver)
        compile_workflow.invoke(initial_state, {"configurable": {"thread_id": job_id}})
        logger.info("Draft task completed")
