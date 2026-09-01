"""
The API's single error shape.

Every non-2xx response body is::

    {"error": {"code": "...", "message": "..."}}

Success responses are bare — an array or an object, never wrapped — because
that is what the frontend client (frontend/src/utils/api.ts) parses.

DRF's default handler renders ``{"detail": ...}`` (or a field-error dict),
which would leak a second error shape into the API the moment any view raised
an APIException. :func:`counsel_exception_handler` normalizes those onto the
envelope; :class:`ApiError` is what view code raises deliberately.
"""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def error_body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


def error_response(code: str, message: str, status_code: int) -> Response:
    return Response(error_body(code, message), status=status_code)


class ApiError(APIException):
    """An error the API raises on purpose, carrying its own code and status."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(detail=message, code=code)


def counsel_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF ``EXCEPTION_HANDLER``: force every handled error onto the envelope."""
    if isinstance(exc, ApiError):
        return error_response(exc.code, exc.message, exc.status_code)

    response = drf_exception_handler(exc, context)
    if response is None:
        # Not an exception DRF knows how to render; let Django's handler turn
        # it into a 500 so the traceback still reaches the logs.
        return None

    code = _code_for_status(response.status_code)
    response.data = error_body(code, _message_from_detail(response.data))
    return response


def _code_for_status(status_code: int) -> str:
    if status_code == status.HTTP_404_NOT_FOUND:
        return "not_found"
    if status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        return "method_not_allowed"
    if status_code < 500:
        return "invalid_request"
    return "server_error"


def _message_from_detail(detail: Any) -> str:
    """Flatten DRF's detail (a string, list, or nested dict) into one message."""
    if isinstance(detail, dict):
        if "detail" in detail:
            return _message_from_detail(detail["detail"])
        return "; ".join(
            f"{field}: {_message_from_detail(value)}" for field, value in detail.items()
        )
    if isinstance(detail, (list, tuple)):
        return "; ".join(_message_from_detail(item) for item in detail)
    return str(detail)
