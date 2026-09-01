"""
The API's single error shape.

Every non-2xx response body is::

    {"error": {"code": "...", "message": "..."}}

Success responses are bare — an array or an object, never wrapped — because
that is what the frontend client (frontend/src/utils/api.ts) parses.

FastAPI's defaults render ``{"detail": ...}``: a string for ``HTTPException``,
a list of per-field records for a request that fails validation. Either would
leak a second error shape into the API, so :func:`install_error_handlers`
replaces all of them. There is no route through this app that produces a body
other than the envelope above.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.http import json_response


class ApiError(Exception):
    """An error the API raises on purpose, carrying its own code and status."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


def error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return json_response(error_body(code, message), status_code)


def install_error_handlers(app: FastAPI) -> None:
    """Point every error path at :func:`error_response`."""

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.code, exc.message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # A malformed body is a bad request, and the endpoints document it as a
        # 400 with this code; FastAPI's own 422 never reaches a client.
        return error_response("invalid_request", _flatten_validation(exc), 400)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # Covers the responses the framework produces on its own: an unknown
        # path (404), a known path with the wrong method (405).
        return error_response(
            _code_for_status(exc.status_code), str(exc.detail), exc.status_code
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Starlette re-raises after this returns, so the traceback still
        # reaches the logs.
        return error_response("server_error", str(exc), 500)


def _code_for_status(status_code: int) -> str:
    if status_code == 404:
        return "not_found"
    if status_code == 405:
        return "method_not_allowed"
    if status_code < 500:
        return "invalid_request"
    return "server_error"


def _flatten_validation(exc: RequestValidationError) -> str:
    """Turn pydantic's per-field error list into one human-readable message."""
    parts: list[str] = []
    for error in exc.errors():
        location: Any = error.get("loc", ())
        # Drop the leading "body"/"query" segment; the field name is what's
        # useful to the caller.
        field = ".".join(str(item) for item in tuple(location)[1:]) or "request"
        parts.append(f"{field}: {error.get('msg', 'invalid')}")
    return "; ".join(parts) or "invalid request"
