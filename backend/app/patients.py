"""Read access to patients, mapped to the ApiUser DTO."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from app.db import one, query
from app.dto import ApiUser
from app.schema import patients

SELECT_PATIENT = select(patients.c.id, patients.c.name)


def to_user(row: Mapping[str, Any]) -> ApiUser:
    return ApiUser(id=row["id"], name=row["name"], is_physician=False)


async def list_patients() -> list[ApiUser]:
    result = await query(SELECT_PATIENT)
    return [to_user(row) for row in result.rows]


async def get_patient_by_id(patient_id: str) -> ApiUser | None:
    row = await one(SELECT_PATIENT.where(patients.c.id == patient_id))
    return to_user(row) if row else None


async def get_patient_by_phone(phone: str) -> ApiUser | None:
    """
    Resolve the patient registered at a given phone number.

    Used by the inbound Relay webhook to map an inbound message's ``from``
    address to a patient. Returns None when no patient is registered at that
    number.
    """
    row = await one(SELECT_PATIENT.where(patients.c.phone == phone))
    return to_user(row) if row else None
