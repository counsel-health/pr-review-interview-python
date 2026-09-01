"""
How a success response is built.

Mirrors ``src/server/http.ts`` in the reference implementation: routes hand a
DTO to :func:`json_response` and get back a fully-formed response, so response
construction is explicit and identical everywhere instead of being inferred
from a route's return annotation. Error responses go through
:func:`app.api.errors.error_response`, which is built on top of this.
"""

from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def json_response[T](data: T, status: int = 200) -> JSONResponse:
    """Serialize ``data`` — a DTO, a list of DTOs, or a plain mapping — as the
    body of a JSON response."""
    return JSONResponse(jsonable_encoder(data), status_code=status)
