from waygate_core.plugin import DispatchErrorKind, WorkflowDispatchResult


def map_dispatch_failure_to_http(
    result: WorkflowDispatchResult,
) -> tuple[int, str]:
    detail = result.detail or "Failed to submit workflow trigger message"

    if result.error_kind == DispatchErrorKind.VALIDATION:
        return (422, detail)
    if result.error_kind == DispatchErrorKind.CONFIG:
        return (503, detail)
    if result.error_kind == DispatchErrorKind.TRANSIENT:
        return (502, detail)

    return (500, detail)
