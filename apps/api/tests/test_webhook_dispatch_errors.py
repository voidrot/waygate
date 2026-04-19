from waygate_api.routes.webhooks.errors import map_dispatch_failure_to_http
from waygate_core.plugin import DispatchErrorKind, WorkflowDispatchResult


def test_map_dispatch_failure_validation() -> None:
    status_code, detail = map_dispatch_failure_to_http(
        WorkflowDispatchResult(
            accepted=False,
            detail="invalid payload",
            error_kind=DispatchErrorKind.VALIDATION,
        )
    )

    assert status_code == 422
    assert detail == "invalid payload"


def test_map_dispatch_failure_config() -> None:
    status_code, detail = map_dispatch_failure_to_http(
        WorkflowDispatchResult(
            accepted=False,
            detail="missing plugin config",
            error_kind=DispatchErrorKind.CONFIG,
        )
    )

    assert status_code == 503
    assert detail == "missing plugin config"


def test_map_dispatch_failure_transient() -> None:
    status_code, detail = map_dispatch_failure_to_http(
        WorkflowDispatchResult(
            accepted=False,
            detail="upstream timeout",
            error_kind=DispatchErrorKind.TRANSIENT,
        )
    )

    assert status_code == 502
    assert detail == "upstream timeout"


def test_map_dispatch_failure_default_permanent() -> None:
    status_code, detail = map_dispatch_failure_to_http(
        WorkflowDispatchResult(
            accepted=False,
            detail="unexpected worker response",
            error_kind=DispatchErrorKind.PERMANENT,
        )
    )

    assert status_code == 500
    assert detail == "unexpected worker response"
