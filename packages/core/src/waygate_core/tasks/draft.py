from waygate_core.workflow.compile import compile_graph
from waygate_core.schema import GraphState
from celery.utils.log import get_task_logger
from waygate_core.logging.helpers import get_wrapped_logger
from celery import shared_task

logger = get_wrapped_logger(get_task_logger(__name__))


@shared_task(pydantic=True)
def new_draft(initial_state: GraphState) -> None:
    logger.info(
        "Starting new draft task", num_documents=len(initial_state.source_documents)
    )
    compile_workflow = compile_graph()
    compile_workflow.invoke(initial_state)
    logger.info("Draft task completed")
