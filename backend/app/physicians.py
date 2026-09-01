"""Read access to physicians, mapped to the ApiUser DTO."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from app.db import one, query
from app.dto import ApiUser
from app.schema import physicians

SELECT_PHYSICIAN = select(physicians.c.id, physicians.c.name)


def to_user(row: Mapping[str, Any]) -> ApiUser:
    return ApiUser(id=row["id"], name=row["name"], is_physician=True)


async def list_physicians() -> list[ApiUser]:
    result = await query(SELECT_PHYSICIAN)
    return [to_user(row) for row in result.rows]


async def get_physician_by_id(physician_id: str) -> ApiUser | None:
    row = await one(SELECT_PHYSICIAN.where(physicians.c.id == physician_id))
    return to_user(row) if row else None
