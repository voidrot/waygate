from waygate_core.plugin import DispatchErrorKind, WorkflowDispatchResult

from waygate_webhooks.errors import map_dispatch_failure_to_http


def test_map_dispatch_failure_to_http_uses_expected_status_codes() -> None:
    validation = WorkflowDispatchResult(
        accepted=False,
        error_kind=DispatchErrorKind.VALIDATION,
        detail="bad payload",
    )
    config = WorkflowDispatchResult(
        accepted=False,
        error_kind=DispatchErrorKind.CONFIG,
        detail="transport unavailable",
    )
    transient = WorkflowDispatchResult(
        accepted=False,
        error_kind=DispatchErrorKind.TRANSIENT,
        detail="nats timeout",
    )
    unknown = WorkflowDispatchResult(accepted=False, detail="unexpected")

    assert map_dispatch_failure_to_http(validation) == (422, "bad payload")
    assert map_dispatch_failure_to_http(config) == (503, "transport unavailable")
    assert map_dispatch_failure_to_http(transient) == (502, "nats timeout")
    assert map_dispatch_failure_to_http(unknown) == (500, "unexpected")
