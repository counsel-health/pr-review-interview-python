"""
The union view over the two user tables.

Patients and physicians are separate tables because they are separate things
in the product, but the UI consumes a single flat list keyed by id.
"""

from __future__ import annotations

from app.dto import ApiUser, UserRole
from app.patients import get_patient_by_id, list_patients
from app.physicians import get_physician_by_id, list_physicians


async def list_all_users() -> list[ApiUser]:
    """Every patient and physician, unioned as a flat ApiUser list."""
    return [*await list_patients(), *await list_physicians()]


async def resolve_role(user_id: str) -> UserRole:
    """
    Resolve a user id to its role by checking patients, then physicians.

    Raises:
        ValueError: if the id belongs to neither table.
    """
    if await get_patient_by_id(user_id):
        return "patient"
    if await get_physician_by_id(user_id):
        return "physician"
    raise ValueError(f"unknown user id: {user_id}")
