"""Trace-id propagation + structured HTTPException responses."""
from __future__ import annotations

import uuid
from typing import Awaitable, Callable

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


TRACE_HEADER = "X-Trace-Id"


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable],
    ):
        trace_id = request.headers.get(TRACE_HEADER) or uuid.uuid4().hex[:16]
        request.state.trace_id = trace_id
        structlog.contextvars.bind_contextvars(trace_id=trace_id, path=request.url.path)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("trace_id", "path")
        response.headers[TRACE_HEADER] = trace_id
        return response


def register_error_handlers(app: FastAPI) -> None:
    log = structlog.get_logger("http.error")

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException):
        trace_id = getattr(request.state, "trace_id", None)
        log.info("http.exception", status=exc.status_code, detail=str(exc.detail))
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "error": str(exc.detail) if not isinstance(exc.detail, dict) else "http_error",
                "detail": exc.detail,
                "trace_id": trace_id,
            },
            headers={TRACE_HEADER: trace_id or ""},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        trace_id = getattr(request.state, "trace_id", None)
        log.exception("http.unhandled", error=repr(exc))
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "detail": str(exc)[:500],
                "trace_id": trace_id,
            },
            headers={TRACE_HEADER: trace_id or ""},
        )
