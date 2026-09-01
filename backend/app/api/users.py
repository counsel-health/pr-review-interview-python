"""
REST endpoint for users.

- ``GET /api/users`` — every patient and physician as a flat ``ApiUser`` list.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.errors import ApiError
from app.api.http import json_response
from app.users import list_all_users

router = APIRouter()


@router.get("/users", response_model=None)
async def get_users() -> JSONResponse:
    try:
        return json_response(await list_all_users())
    except Exception as exc:
        raise ApiError("users_failed", str(exc), 500) from exc
