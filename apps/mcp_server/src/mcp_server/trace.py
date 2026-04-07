from __future__ import annotations

from contextvars import ContextVar, Token
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware


_current_trace_id: ContextVar[str | None] = ContextVar(
    "waygate_mcp_trace_id", default=None
)


def get_current_trace_id() -> str | None:
    return _current_trace_id.get()


def set_current_trace_id(trace_id: str | None) -> Token[str | None]:
    return _current_trace_id.set(trace_id)


def reset_current_trace_id(token: Token[str | None]) -> None:
    _current_trace_id.reset(token)


class TraceContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("x-trace-id") or str(uuid4())
        token = set_current_trace_id(trace_id)
        try:
            response = await call_next(request)
        finally:
            reset_current_trace_id(token)

        response.headers["x-trace-id"] = trace_id
        return response
